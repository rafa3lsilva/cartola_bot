import pulp
import pandas as pd

class TeamOptimizer:
    """Classe responsável por resolver o problema de otimização linear da escalação com PuLP."""
    def __init__(self, config):
        self.config = config
        self.formations = config.get('formations', {})
        self.weights = config.get('scoring', {}).get('weights', {})
        self.upside_lambda_atk = self.weights.get('upside_lambda_atk', 0.25)
        self.upside_lambda_def = self.weights.get('upside_lambda_def', 0.12)
        self.captain_upside_weight = self.weights.get('captain_upside_weight', 0.50)
        self.top_scorer_weight = self.weights.get('top_scorer_weight', 0.35)
        self.max_defenders_per_club = config.get('defaults', {}).get('max_defenders_per_club', 2)
        self.avoid_conflict_default = config.get('defaults', {}).get('avoid_attack_vs_defense_conflict', True)

    def optimize(self, df, budget, formation_name, max_players_per_club=None, avoid_attack_vs_defense_conflict=None):
        """Usa Programação Linear Inteira Mista (MILP) para encontrar o time ideal com Capitão integrado e foco em alto teto (upside)."""
        reqs = self.formations.get(formation_name)
        if not reqs:
            raise ValueError(f"Formação '{formation_name}' não suportada.")

        if avoid_attack_vs_defense_conflict is None:
            avoid_attack_vs_defense_conflict = self.avoid_conflict_default

        ids = df['ID'].tolist()
        precos = dict(zip(ids, df['Preco']))
        medias = dict(zip(ids, df['Media_Ajustada']))
        posicoes = dict(zip(ids, df['Posicao']))
        clubes = dict(zip(ids, df['Clube']))
        upsides = dict(zip(ids, df['Upside'])) if 'Upside' in df.columns else medias
        goals_pg = dict(zip(ids, df['Goals_Per_Game'])) if 'Goals_Per_Game' in df.columns else {}
        
        # Mapeamento de adversários para cada clube a partir de Opp_Abrev ou Confronto
        opp_by_club = {}
        for _, row in df.iterrows():
            c = row.get('Clube')
            if c and c not in opp_by_club:
                opp = row.get('Opp_Abrev')
                if not opp or pd.isna(opp):
                    conf = str(row.get('Confronto', ''))
                    parts = conf.split()
                    if len(parts) >= 2:
                        opp = parts[1]
                if opp and not pd.isna(opp) and opp != 'ADV':
                    opp_by_club[c] = str(opp).strip()
        
        # Calcular scores efetivos combinando média esperada + peso de teto por posição e faro de gol
        effective_scores = {}
        cap_scores = {}
        for i in ids:
            pos = posicoes[i]
            m = medias[i]
            u = upsides.get(i, m)
            diff = max(0.0, u - m)
            
            if pos in ['Meia', 'Atacante']:
                effective_scores[i] = m + self.upside_lambda_atk * diff
                # Fator Artilheiro: atacantes/meias de alto volume de gols (ex: Viveros) ganham preferência para capitão
                gpg = goals_pg.get(i, 0.0)
                artilheiro_factor = 1.0 + min(0.35, gpg * self.top_scorer_weight)
                cap_scores[i] = 0.50 * (m + self.captain_upside_weight * diff) * artilheiro_factor
            elif pos in ['Lateral', 'Zagueiro']:
                effective_scores[i] = m + self.upside_lambda_def * diff
                cap_scores[i] = 0.50 * (m + 0.15 * diff)
            elif pos == 'Goleiro':
                effective_scores[i] = m + 0.08 * diff
                cap_scores[i] = 0.50 * m
            else:  # Técnico
                effective_scores[i] = m
                cap_scores[i] = 0.0
        
        # 1. Variáveis de Decisão (compatível com todas as versões do PuLP)
        player_vars = {i: pulp.LpVariable(f"Atleta_{i}", cat="Binary") for i in ids}
        captain_vars = {i: pulp.LpVariable(f"Capitao_{i}", cat="Binary") for i in ids}
        
        prob = pulp.LpProblem(f"Otimizador_Cartola_{formation_name}", pulp.LpMaximize)
        
        # 2. Função Objetivo: Maximizar Pontuação Total Esperada + Upside (com Capitão 1.5x)
        prob += pulp.lpSum([
            effective_scores[i] * player_vars[i] + cap_scores[i] * captain_vars[i] 
            for i in ids
        ]), "Total_Pontos_Esperados_Upside"
        
        # 3. Restrição de Orçamento
        prob += pulp.lpSum([precos[i] * player_vars[i] for i in ids]) <= budget, "Custo_Total"
        
        # 4. Restrições de Posição
        for pos, limit in reqs.items():
            prob += pulp.lpSum([player_vars[i] for i in ids if posicoes[i] == pos]) == limit, f"Posicao_{pos}"
            
        # 5. Restrições do Capitão
        # Exatamente 1 capitão
        prob += pulp.lpSum([captain_vars[i] for i in ids]) == 1, "Exatamente_Um_Capitao"
        
        for i in ids:
            # Capitão precisa estar entre os titulares
            prob += captain_vars[i] <= player_vars[i], f"Capitao_Titular_{i}"
            
            # Técnico não pode ser capitão
            if posicoes[i] == 'Técnico':
                prob += captain_vars[i] == 0, f"Tecnico_Nao_Capitao_{i}"
                
        # 6. Restrição de limite de atletas por clube (mitigação de risco geral)
        if max_players_per_club and max_players_per_club > 0:
            unique_clubs = set(clubes.values())
            for club in unique_clubs:
                prob += pulp.lpSum([player_vars[i] for i in ids if clubes[i] == club]) <= max_players_per_club, f"Max_Clube_{club}"

        # 6.1. Restrição de limite de defensores por clube (evita ruína de SG quádruplo)
        def_positions = {'Goleiro', 'Lateral', 'Zagueiro'}
        if self.max_defenders_per_club and self.max_defenders_per_club > 0:
            unique_clubs = set(clubes.values())
            for club in unique_clubs:
                prob += pulp.lpSum([
                    player_vars[i] for i in ids 
                    if clubes[i] == club and posicoes[i] in def_positions
                ]) <= self.max_defenders_per_club, f"Max_Defensores_Clube_{club}"

        # 6.2. Restrição Anti-Conflito: Evita Ataque/Meia contra Defesa Adversária (Protege SG)
        if avoid_attack_vs_defense_conflict and opp_by_club:
            atk_mid_positions = {'Meia', 'Atacante'}
            # Para cada par ordenado (Clube A defensor vs Clube B atacante) onde Clube B é o adversário de Clube A:
            for c_def, c_atk in opp_by_club.items():
                def_ids = [i for i in ids if clubes[i] == c_def and posicoes[i] in def_positions]
                atk_ids = [i for i in ids if clubes[i] == c_atk and posicoes[i] in atk_mid_positions]
                
                if def_ids and atk_ids:
                    # Variável binária: 1 se escalar algum defensor do c_def; 0 caso contrário
                    y_def = pulp.LpVariable(f"HasDef_{c_def}_vs_{c_atk}", cat="Binary")
                    # Se y_def == 1 -> pode escalar defensores de c_def (até o limite) e 0 atacantes/meias de c_atk
                    # Se y_def == 0 -> 0 defensores de c_def e pode escalar atacantes/meias de c_atk
                    max_def_count = min(len(def_ids), reqs.get('Goleiro', 1) + reqs.get('Lateral', 2) + reqs.get('Zagueiro', 3))
                    max_atk_count = min(len(atk_ids), reqs.get('Meia', 3) + reqs.get('Atacante', 3))
                    
                    prob += pulp.lpSum([player_vars[i] for i in def_ids]) <= max_def_count * y_def, f"ConflictDef_{c_def}_vs_{c_atk}"
                    prob += pulp.lpSum([player_vars[i] for i in atk_ids]) <= max_atk_count * (1 - y_def), f"ConflictAtk_{c_atk}_vs_{c_def}"
                
        # 7. Resolver Modelo
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        
        if pulp.LpStatus[prob.status] != 'Optimal':
            return None
            
        selected_ids = [i for i in ids if player_vars[i].varValue == 1]
        captain_ids = [i for i in ids if captain_vars[i].varValue == 1]
        captain_id = captain_ids[0] if captain_ids else None
        
        result_df = df[df['ID'].isin(selected_ids)].copy()
        result_df['Is_Capitao'] = result_df['ID'] == captain_id
        
        return result_df

    def optimize_best_formation(self, df, budget, max_players_per_club=None, avoid_attack_vs_defense_conflict=None):
        """Avalia todas as formações cadastradas e retorna a melhor escalação global."""
        best_formation = None
        best_df = None
        best_score = -1.0
        all_results = {}
        
        for formation_name in self.formations.keys():
            res_df = self.optimize(
                df, budget, formation_name, 
                max_players_per_club=max_players_per_club,
                avoid_attack_vs_defense_conflict=avoid_attack_vs_defense_conflict
            )
            if res_df is not None:
                # Calcular pontuação total (soma + bônus de 50% oficial do capitão)
                cap_bonus = res_df[res_df['Is_Capitao']]['Media_Ajustada'].sum() * 0.5
                total_score = res_df['Media_Ajustada'].sum() + cap_bonus
                
                all_results[formation_name] = {
                    'df': res_df,
                    'score': round(total_score, 2),
                    'cost': round(res_df['Preco'].sum(), 2)
                }
                
                if total_score > best_score:
                    best_score = total_score
                    best_df = res_df
                    best_formation = formation_name
                    
        return best_formation, best_df, best_score, all_results

    def get_reservas(self, df, selected_df):
        """Retorna o 'Reserva de Luxo' para cada posição (exceto Técnico) focado no maior teto de pontos."""
        reservas = {}
        selected_ids = selected_df['ID'].tolist()
        
        for pos in ['Goleiro', 'Lateral', 'Zagueiro', 'Meia', 'Atacante']:
            titulares = selected_df[selected_df['Posicao'] == pos]
            if titulares.empty:
                continue
                
            cheapest_starter_price = titulares['Preco'].min()
            worst_starter_xp = titulares['Media_Ajustada'].min()
            
            # Regra oficial: reserva deve custar <= ao titular mais barato daquela posição
            candidates = df[
                (df['Posicao'] == pos) & 
                (~df['ID'].isin(selected_ids)) & 
                (df['Preco'] <= cheapest_starter_price)
            ].copy()
            
            if not candidates.empty:
                # Priorizar maior Teto / Upside para maximizar a chance e impacto da troca automática
                if 'Upside' in candidates.columns:
                    candidates = candidates.sort_values(by=['Upside', 'Media_Ajustada'], ascending=[False, False])
                else:
                    candidates = candidates.sort_values(by='Media_Ajustada', ascending=False)
                    
                best_res = candidates.iloc[0].to_dict()
                res_xp = best_res.get('Media_Ajustada', 0)
                res_upside = best_res.get('Upside', res_xp)
                
                # Ganho esperado adicional caso o reserva supere o pior titular
                expected_gain = round(max(0.0, (res_upside - worst_starter_xp) * 0.4), 2)
                best_res['Expected_Gain'] = expected_gain
                best_res['Worst_Starter_XP'] = worst_starter_xp
                
                reservas[pos] = pd.Series(best_res)
                
        return reservas

    def analyze_user_lineup(self, df, selected_df, captain_id=None, budget=146.07):
        """Analisa a escalação escolhida pelo usuário e gera diagnóstico detalhado atleta por atleta."""
        if selected_df.empty:
            return None
            
        selected_ids = selected_df['ID'].tolist()
        total_cost = float(selected_df['Preco'].sum())
        budget_left = round(budget - total_cost, 2)
        
        # Identificar capitão
        if captain_id is None or captain_id not in selected_ids:
            cap_idx = selected_df['Media_Ajustada'].idxmax()
            captain_id = selected_df.loc[cap_idx, 'ID']
            
        cap_row = selected_df[selected_df['ID'] == captain_id].iloc[0]
        cap_extra = float(cap_row['Media_Ajustada'] * 0.4)
        total_xp = round(float(selected_df['Media_Ajustada'].sum() + cap_extra), 2)
        
        starters_analysis = []
        manter_count = 0
        atencao_count = 0
        trocar_count = 0
        total_gain_potential = 0.0

        # Mapeamento de defensores escalados por clube
        def_positions = {'Goleiro', 'Lateral', 'Zagueiro'}
        atk_positions = {'Meia', 'Atacante'}
        def_clubs_escalados = set(selected_df[selected_df['Posicao'].isin(def_positions)]['Clube'].unique())
        
        # Mapeamento de adversários para cada clube
        opp_by_club = {}
        for _, row in df.iterrows():
            c = row.get('Clube')
            if c and c not in opp_by_club:
                opp = row.get('Opp_Abrev')
                if not opp or pd.isna(opp):
                    conf = str(row.get('Confronto', ''))
                    parts = conf.split()
                    if len(parts) >= 2:
                        opp = parts[1]
                if opp and not pd.isna(opp) and opp != 'ADV':
                    opp_by_club[c] = str(opp).strip()

        conflict_warnings = []

        for _, p in selected_df.iterrows():
            p_id = p['ID']
            pos = p['Posicao']
            preco = float(p['Preco'])
            xp = float(p['Media_Ajustada'])
            clube = p['Clube']
            is_cap = (p_id == captain_id)
            xp_final = xp * 1.4 if is_cap else xp
            
            tag = p.get('Tag', 'Boa Opção')
            tag_color = p.get('Tag_Color', '#f59e0b')
            status_cons = p.get('Status_Consultoria', 'MANTER')
            just = p.get('Justificativa', 'Atleta escalado pelo usuário.')
            
            # Detecção de conflito: Atacante/Meia enfrentando a defesa que você próprio escalou
            has_sg_conflict = False
            opp_club = opp_by_club.get(clube)
            if pos in atk_positions and opp_club and opp_club in def_clubs_escalados:
                has_sg_conflict = True
                def_rivals = selected_df[(selected_df['Clube'] == opp_club) & (selected_df['Posicao'].isin(def_positions))]['Nome'].tolist()
                def_str = ", ".join(def_rivals)
                conflict_msg = f"⚔️ **Conflito de SG:** Enfrenta a sua defesa ({opp_club}: {def_str})."
                just = f"{conflict_msg} {just}"
                conflict_warnings.append(f"{p['Nome']} ({clube}) vs {def_str} ({opp_club})")
                if status_cons == 'MANTER':
                    status_cons = 'ATENCAO'
                    tag = 'Atenção (Conflito SG)'
                    tag_color = '#f59e0b'
            
            if status_cons == 'MANTER':
                manter_count += 1
            elif status_cons == 'ATENCAO':
                atencao_count += 1
            else:
                trocar_count += 1
                
            # Buscar melhor alternativa de troca na mesma posição
            # Alternativa viável: não estar no time, preço <= preco + max(0, budget_left), e com maior xP
            max_afford_price = preco + max(0.0, budget_left)
            candidates = df[
                (df['Posicao'] == pos) & 
                (~df['ID'].isin(selected_ids)) & 
                (df['Preco'] <= max_afford_price) & 
                (df['Media_Ajustada'] > xp + 0.6)
            ].sort_values(by='Media_Ajustada', ascending=False)
            
            sugestao = None
            if not candidates.empty:
                best_cand = candidates.iloc[0]
                cand_xp = float(best_cand['Media_Ajustada'])
                cand_preco = float(best_cand['Preco'])
                delta_xp = round(cand_xp - xp, 2)
                delta_preco = round(preco - cand_preco, 2)
                
                sugestao = {
                    'ID': best_cand['ID'],
                    'Nome': best_cand['Nome'],
                    'Clube': best_cand['Clube'],
                    'Posicao': pos,
                    'Preco': cand_preco,
                    'xP': cand_xp,
                    'Delta_xP': delta_xp,
                    'Delta_Preco': delta_preco,
                    'Tag': best_cand.get('Tag', 'Excelente'),
                    'Justificativa': best_cand.get('Justificativa', '')
                }
                total_gain_potential += delta_xp

            starters_analysis.append({
                'ID': p_id,
                'Nome': p['Nome'],
                'Posicao': pos,
                'Clube': p['Clube'],
                'Preco': preco,
                'Media_Ajustada': xp,
                'xP_Final': round(xp_final, 2),
                'Upside': p.get('Upside', xp),
                'SG_Prob': p.get('SG_Prob', None),
                'Foto': p.get('Foto', ''),
                'Escudo': p.get('Escudo', ''),
                'Confronto': p.get('Confronto', ''),
                'Tag': tag,
                'Tag_Color': tag_color,
                'Status_Consultoria': status_cons,
                'Justificativa': just,
                'Is_Capitao': is_cap,
                'Has_SG_Conflict': has_sg_conflict,
                'Sugestao_Troca': sugestao
            })

        # Veredito Geral da Escalação
        if conflict_warnings:
            rating = "⚔️ Escalação com Conflito de SG"
            rating_color = "#f59e0b"
            rating_desc = f"Atenção: Você tem atletas ofensivos enfrentando sua própria defesa ({'; '.join(conflict_warnings)}). Gols marcados anularão o SG da sua zaga."
        elif trocar_count == 0 and atencao_count <= 2 and total_xp >= 92.0:
            rating = "🔥 Escalação de Elite (Muito Forte)"
            rating_color = "#10b981"
            rating_desc = "Seu time está muito bem balanceado, sem canibalização de SG e explorando os melhores mandantes com alto teto."
        elif trocar_count <= 2:
            rating = "⚖️ Escalação Competitiva"
            rating_color = "#f59e0b"
            rating_desc = "Time competitivo com bom teto de pontos. Existem 1 ou 2 ajustes pontuais que podem elevar ainda mais o potencial."
        else:
            rating = "⚠️ Escalação Arriscada"
            rating_color = "#ef4444"
            rating_desc = "Você possui jogadores com confrontos difíceis fora de casa ou preço muito elevado pelo retorno esperado. Recomendamos avaliar as trocas sugeridas."

        return {
            'total_cost': total_cost,
            'budget_left': budget_left,
            'total_xp': total_xp,
            'captain_name': cap_row['Nome'],
            'captain_id': captain_id,
            'starters': starters_analysis,
            'manter_count': manter_count,
            'atencao_count': atencao_count,
            'trocar_count': trocar_count,
            'conflict_warnings': conflict_warnings,
            'rating': rating,
            'rating_color': rating_color,
            'rating_desc': rating_desc,
            'total_gain_potential': round(total_gain_potential, 2)
        }

