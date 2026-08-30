import pulp
import pandas as pd

class TeamOptimizer:
    """Classe responsável por resolver o problema de otimização linear da escalação com PuLP."""
    def __init__(self, config):
        self.formations = config['formations']

    def optimize(self, df, budget, formation_name, max_players_per_club=None):
        """Usa Programação Linear Inteira Mista (MILP) para encontrar o time ideal com Capitão integrado."""
        reqs = self.formations.get(formation_name)
        if not reqs:
            raise ValueError(f"Formação '{formation_name}' não suportada.")

        ids = df['ID'].tolist()
        precos = dict(zip(ids, df['Preco']))
        medias = dict(zip(ids, df['Media_Ajustada']))
        posicoes = dict(zip(ids, df['Posicao']))
        clubes = dict(zip(ids, df['Clube']))
        
        # 1. Variáveis de Decisão
        player_vars = pulp.LpVariable.dicts("Atleta", ids, cat="Binary")
        captain_vars = pulp.LpVariable.dicts("Capitao", ids, cat="Binary")
        
        prob = pulp.LpProblem(f"Otimizador_Cartola_{formation_name}", pulp.LpMaximize)
        
        # 2. Função Objetivo: Maximizar Pontuação Total Esperada (com Capitão 1.5x)
        prob += pulp.lpSum([
            medias[i] * player_vars[i] + 0.5 * medias[i] * captain_vars[i] 
            for i in ids
        ]), "Total_Pontos_Esperados"
        
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
                
        # 6. Restrição de limite de atletas por clube (mitigação de risco)
        if max_players_per_club and max_players_per_club > 0:
            unique_clubs = set(clubes.values())
            for club in unique_clubs:
                prob += pulp.lpSum([player_vars[i] for i in ids if clubes[i] == club]) <= max_players_per_club, f"Max_Clube_{club}"
                
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

    def optimize_best_formation(self, df, budget, max_players_per_club=None):
        """Avalia todas as formações cadastradas e retorna a melhor escalação global."""
        best_formation = None
        best_df = None
        best_score = -1.0
        all_results = {}
        
        for formation_name in self.formations.keys():
            res_df = self.optimize(df, budget, formation_name, max_players_per_club)
            if res_df is not None:
                # Calcular pontuação total (soma + bônus de 50% do capitão)
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
        cap_extra = float(cap_row['Media_Ajustada'] * 0.5)
        total_xp = round(float(selected_df['Media_Ajustada'].sum() + cap_extra), 2)
        
        starters_analysis = []
        manter_count = 0
        atencao_count = 0
        trocar_count = 0
        total_gain_potential = 0.0

        for _, p in selected_df.iterrows():
            p_id = p['ID']
            pos = p['Posicao']
            preco = float(p['Preco'])
            xp = float(p['Media_Ajustada'])
            is_cap = (p_id == captain_id)
            xp_final = xp * 1.5 if is_cap else xp
            
            tag = p.get('Tag', 'Boa Opção')
            tag_color = p.get('Tag_Color', '#f59e0b')
            status_cons = p.get('Status_Consultoria', 'MANTER')
            just = p.get('Justificativa', 'Atleta escalado pelo usuário.')
            
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
                'Sugestao_Troca': sugestao
            })

        # Veredito Geral da Escalação
        if trocar_count == 0 and atencao_count <= 2 and total_xp >= 92.0:
            rating = "🔥 Escalação de Elite (Muito Forte)"
            rating_color = "#10b981"
            rating_desc = "Seu time está muito bem balanceado, explorando os melhores mandantes e defesas com alta probabilidade de SG."
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
            'rating': rating,
            'rating_color': rating_color,
            'rating_desc': rating_desc,
            'total_gain_potential': round(total_gain_potential, 2)
        }

