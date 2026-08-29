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
                
        return reservas

