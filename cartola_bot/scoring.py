import pandas as pd
import numpy as np

class Scorer:
    """Classe responsável pelo processamento estatístico e cálculo de pontuação esperada (xP) e teto de pontos."""
    def __init__(self, config):
        self.config = config['scoring']
        self.defaults = config['defaults']

    def process_data(self, mercado_data, partidas_data, target_athlete_ids=None):
        """Processa os dados brutos e calcula o xP com Fator Momento e Matriz de Cedência de Scouts."""
        atletas = mercado_data.get('atletas', [])
        clubes = mercado_data.get('clubes', {})
        posicoes = mercado_data.get('posicoes', {})
        
        # 1. Mapeamento das partidas com Fator Momento
        partidas_info = self._process_partidas(partidas_data)
        weights = self.config.get('weights', {})
        
        home_atk_mult = weights.get('home_attack_multiplier', 1.15)
        away_atk_mult = weights.get('away_attack_multiplier', 0.85)
        opp_weight = weights.get('opp_strength_weight', 0.015)
        
        # 2. Matriz de Cedência de Scouts Coletiva por Clube
        club_concessions = self._calculate_club_concessions(atletas)
        
        processed = []
        club_line_players = {}
        target_ids_set = {int(x) for x in target_athlete_ids} if target_athlete_ids else set()
        
        for a in atletas:
            a_id = a.get('atleta_id')
            is_target = a_id in target_ids_set
            if a.get('status_id') != 7 and not is_target: # Apenas prováveis ou alvos fixados
                continue
                
            pos_id = str(a.get('posicao_id', ''))
            clube_id = str(a.get('clube_id', ''))
            
            posicao = posicoes.get(pos_id, {}).get('nome', 'Desconhecida')
            clube = clubes.get(clube_id, {}).get('nome', 'Desconhecido')
            
            media_bruta = float(a.get('media_num', 0) or 0)
            preco = float(a.get('preco_num', 0) or 0)
            jogos = int(a.get('jogos_num', 0) or 0)
            scout = a.get('scout') or {}
            
            matchup = partidas_info.get(clube_id)
            is_home = matchup['is_home'] if matchup else True
            opp_id = matchup.get('opp_id', '') if matchup else ''
            opp_pos = matchup['opp_pos'] if matchup else 10
            sg_prob = matchup['sg_prob'] if matchup else 0.30
            momentum = matchup['momentum'] if matchup else 1.0
            
            # Fatores do adversário obtidos da Matriz de Cedência
            opp_concession = club_concessions.get(opp_id, {
                'defensive_leak': 1.0, 
                'fouls_rate': 1.0, 
                'shots_rate': 1.0
            })
            
            # Fator de mando de campo ajustado pelo Momento Recente da equipe
            mando_factor = (home_atk_mult if is_home else away_atk_mult) * momentum
            
            # Fator de fragilidade da classificação do adversário
            opp_pos_factor = 1.0 + (opp_pos - 10.5) * opp_weight
            
            # Decomposição granular de scouts individuais por jogo
            num_j = max(1, jogos)
            ds_pts = (scout.get('DS', 0) * 1.2) / num_j
            fin_pts = (scout.get('FD', 0)*1.2 + scout.get('FF', 0)*0.8 + scout.get('FT', 0)*3.0) / num_j
            fs_pts = (scout.get('FS', 0) * 0.5) / num_j
            g_pts = (scout.get('G', 0) * 8.0) / num_j
            a_pts = (scout.get('A', 0) * 5.0) / num_j
            de_pts = (scout.get('DE', 0) * 1.0) / num_j
            penal_pts = (scout.get('CA', 0)*-1.0 + scout.get('FC', 0)*-0.3 + scout.get('I', 0)*-0.1) / num_j
            
            # 1. Defensores (Goleiro, Lateral, Zagueiro)
            if posicao in ['Goleiro', 'Lateral', 'Zagueiro']:
                total_sg = scout.get('SG', 0)
                avg_sg_points = (total_sg * 5.0 / num_j) if jogos > 0 else 1.5
                media_basica = max(0.0, media_bruta - avg_sg_points)
                
                # Ajustes específicos por posição defensiva:
                if posicao == 'Goleiro':
                    # Goleiro pontua mais em Defesas (DE) se o adversário finaliza muito (shots_rate)
                    adjusted_de = de_pts * opp_concession['shots_rate']
                    base_est = (media_basica + (adjusted_de - de_pts)) if jogos >= 3 else media_basica
                else:
                    # Laterais e Zagueiros ganham mais desarmes se o rival cede muitas faltas/perdas de posse
                    adjusted_ds = ds_pts * opp_concession['fouls_rate']
                    scout_expectancy = (adjusted_ds + fs_pts + fin_pts + penal_pts + g_pts*0.3 + a_pts*0.3)
                    base_est = (0.5 * media_basica + 0.5 * scout_expectancy) if jogos >= 3 else media_basica
                    
                # xP Defesa = Média básica ajustada + SG esperado
                xp = (base_est * mando_factor * opp_pos_factor) + (5.0 * sg_prob)
                
            # 2. Meias e Atacantes
            elif posicao in ['Meia', 'Atacante']:
                # Atacantes e meias são turbinados se a zaga adversária for vazada (defensive_leak)
                leak_factor = opp_concession['defensive_leak']
                if jogos >= 3:
                    offensive_scouts = (g_pts * leak_factor + a_pts * leak_factor + fin_pts * opp_concession['shots_rate'] + fs_pts * opp_concession['fouls_rate'] + ds_pts + penal_pts)
                    base_est = 0.4 * media_bruta + 0.6 * offensive_scouts
                else:
                    base_est = media_bruta
                    
                xp = base_est * mando_factor * opp_pos_factor * leak_factor
                
            # 3. Técnico
            else:
                xp = media_bruta * mando_factor
                
            xp = round(max(0.0, xp), 2)
            min_valorizar = round(preco * 0.37, 2)
            
            # Teto / Upside (potencial de mitada com Fator Momento)
            upside = round(xp + (g_pts * 1.2 + a_pts * 1.1 + fin_pts*0.6 + ds_pts*0.5), 2)
            
            clube_obj = clubes.get(clube_id, {})
            clube_nome = clube_obj.get('nome', 'Desconhecido')
            clube_abrev = clube_obj.get('abreviacao', clube_nome)
            escudo_url = clube_obj.get('escudos', {}).get('60x60', '')
            foto_url = (a.get('foto') or '').replace('FORMATO', '220x220')

            opp_obj = clubes.get(opp_id, {})
            opp_abrev = opp_obj.get('abreviacao', 'ADV')
            confronto_str = f"{'vs' if is_home else '@'} {opp_abrev} ({'C' if is_home else 'F'})"

            tag, tag_color, status_cons, justificativa = self._generate_tag_and_justification(
                posicao=posicao,
                preco=preco,
                media_bruta=media_bruta,
                xp=xp,
                upside=upside,
                sg_prob_pct=round(sg_prob * 100, 1),
                is_home=is_home,
                opp_abrev=opp_abrev,
                opp_pos=opp_pos,
                scout=scout,
                jogos=jogos
            )

            player_data = {
                'ID': a.get('atleta_id'),
                'Nome': a.get('apelido', 'Sem Nome'),
                'Posicao': posicao,
                'Clube': clube_abrev,
                'Clube_Nome': clube_nome,
                'Clube_ID': clube_id,
                'Preco': preco,
                'Media': media_bruta,
                'Min_Val': min_valorizar,
                'Media_Ajustada': xp,
                'Upside': upside,
                'SG_Prob': round(sg_prob * 100, 1),
                'Jogos': jogos,
                'Foto': foto_url,
                'Escudo': escudo_url,
                'Confronto': confronto_str,
                'Is_Home': is_home,
                'Opp_Abrev': opp_abrev,
                'Tag': tag,
                'Tag_Color': tag_color,
                'Status_Consultoria': status_cons,
                'Justificativa': justificativa
            }
            
            processed.append(player_data)
            
            if posicao != 'Técnico':
                if clube_id not in club_line_players:
                    club_line_players[clube_id] = []
                club_line_players[clube_id].append(xp)

        # Atualizar xP dos Técnicos
        for p in processed:
            if p['Posicao'] == 'Técnico':
                c_id = p['Clube_ID']
                if c_id in club_line_players and len(club_line_players[c_id]) > 0:
                    top_players = sorted(club_line_players[c_id], reverse=True)[:11]
                    p['Media_Ajustada'] = round(float(np.mean(top_players)), 2)
                    p['Upside'] = p['Media_Ajustada']
                    # Atualizar justificativa do técnico com o xP médio final
                    t_xp = p['Media_Ajustada']
                    if t_xp >= 6.5:
                        p['Tag'] = 'Excelente'
                        p['Tag_Color'] = '#10b981'
                        p['Status_Consultoria'] = 'MANTER'
                        p['Justificativa'] = f"Equipe mandante favorita com alta média projetada de titulares ({t_xp:.2f} xP)." if p['Is_Home'] else f"Equipe consistente com ótimo potencial na rodada ({t_xp:.2f} xP)."
                    elif t_xp >= 5.0:
                        p['Tag'] = 'Boa Opção'
                        p['Tag_Color'] = '#f59e0b'
                        p['Status_Consultoria'] = 'MANTER'
                        p['Justificativa'] = f"Confronto equilibrado ({p['Confronto']}), pontuação esperada moderada ({t_xp:.2f} xP)."
                    else:
                        p['Tag'] = 'Evitar'
                        p['Tag_Color'] = '#ef4444'
                        p['Status_Consultoria'] = 'TROCAR'
                        p['Justificativa'] = f"Confronto desfavorável fora de casa; elenco titular com baixa projeção ({t_xp:.2f} xP)."
        
        df = pd.DataFrame(processed)
        
        if not df.empty and df['Jogos'].max() > self.defaults['min_games_threshold']:
            if target_athlete_ids:
                df = df[(df['Jogos'] >= self.defaults['min_games']) | (df['ID'].isin(target_ids_set))].copy()
            else:
                df = df[df['Jogos'] >= self.defaults['min_games']].copy()
            
        return df

    def _calculate_club_concessions(self, atletas):
        """Calcula o índice relativo de cedência de scouts e fragilidade defensiva de cada clube."""
        club_stats = {}
        
        for a in atletas:
            c_id = str(a.get('clube_id', ''))
            scout = a.get('scout') or {}
            pos_id = a.get('posicao_id')
            jogos = max(1, int(a.get('jogos_num', 0) or 0))
            
            if c_id not in club_stats:
                club_stats[c_id] = {'FC': 0, 'GS': 0, 'DE': 0, 'athletes_count': 0}
                
            club_stats[c_id]['FC'] += scout.get('FC', 0)
            if pos_id == 1: # Goleiro
                club_stats[c_id]['GS'] += scout.get('GS', 0)
                club_stats[c_id]['DE'] += scout.get('DE', 0)
            club_stats[c_id]['athletes_count'] += 1
            
        concessions = {}
        avg_fc = np.mean([s['FC'] for s in club_stats.values()]) if club_stats else 1.0
        avg_gs = np.mean([s['GS'] for s in club_stats.values()]) if club_stats else 1.0
        avg_de = np.mean([s['DE'] for s in club_stats.values()]) if club_stats else 1.0
        
        for c_id, stats in club_stats.items():
            fouls_rate = (stats['FC'] / avg_fc) if avg_fc > 0 else 1.0
            defensive_leak = (stats['GS'] / avg_gs) if avg_gs > 0 else 1.0
            shots_rate = (stats['DE'] / avg_de) if avg_de > 0 else 1.0
            
            # Limitar os multiplicadores entre 0.80 e 1.25 para evitar distorções
            concessions[c_id] = {
                'fouls_rate': float(np.clip(fouls_rate, 0.85, 1.20)),
                'defensive_leak': float(np.clip(defensive_leak, 0.80, 1.25)),
                'shots_rate': float(np.clip(shots_rate, 0.85, 1.20))
            }
            
        return concessions

    def _process_partidas(self, partidas_data):
        """Mapeia as partidas e calcula a probabilidade estatística de SG com Fator Momento."""
        partidas_info = {}
        weights = self.config.get('weights', {})
        
        sg_base = weights.get('sg_base_prob', 0.30)
        sg_home = weights.get('sg_home_bonus', 0.15)
        sg_away = weights.get('sg_away_penalty', 0.10)
        opp_weight = weights.get('opp_strength_weight', 0.015)
        
        for p in partidas_data.get('partidas', []):
            casa_id = str(p.get('clube_casa_id'))
            visi_id = str(p.get('clube_visitante_id'))
            casa_pos = p.get('clube_casa_posicao', 10)
            visi_pos = p.get('clube_visitante_posicao', 10)
            
            # 1. Calcular Fator Momento (Aproveitamento recente ponderado)
            form_casa = self._calculate_form_score(p.get('aproveitamento_mandante', []))
            form_visi = self._calculate_form_score(p.get('aproveitamento_visitante', []))
            
            # Multiplicador de momentum para atletas
            momentum_casa = 1.0 + (form_casa - 0.45) * 0.20
            momentum_visi = 1.0 + (form_visi - 0.45) * 0.20
            
            # 2. Probabilidade estimada de SG ajustada por Momento
            form_diff = (form_casa - form_visi) * 0.15
            
            sg_prob_casa = sg_base + sg_home + (visi_pos - casa_pos) * opp_weight + form_diff
            sg_prob_casa = max(0.05, min(0.85, sg_prob_casa))
            
            sg_prob_visi = sg_base - sg_away + (casa_pos - visi_pos) * opp_weight - form_diff
            sg_prob_visi = max(0.05, min(0.80, sg_prob_visi))
            
            partidas_info[casa_id] = {
                'is_home': True, 
                'opp_id': visi_id,
                'opp_pos': visi_pos,
                'sg_prob': sg_prob_casa,
                'momentum': round(float(np.clip(momentum_casa, 0.85, 1.15)), 3)
            }
            partidas_info[visi_id] = {
                'is_home': False, 
                'opp_id': casa_id,
                'opp_pos': casa_pos,
                'sg_prob': sg_prob_visi,
                'momentum': round(float(np.clip(momentum_visi, 0.85, 1.15)), 3)
            }
            
        return partidas_info

    def _calculate_form_score(self, history):
        """Calcula a pontuação de forma recente com pesos maiores nos jogos mais recentes."""
        if not history:
            return 0.45
            
        point_map = {'v': 3.0, 'e': 1.0, 'd': 0.0}
        weights = [0.8, 0.9, 1.0, 1.1, 1.2]
        
        # Ajustar pesos ao tamanho do histórico
        hist_len = len(history)
        w_slice = weights[-hist_len:]
        
        total_pts = sum(point_map.get(str(h).lower(), 0.0) * w for h, w in zip(history, w_slice))
        max_pts = sum(3.0 * w for w in w_slice)
        
        return total_pts / max_pts if max_pts > 0 else 0.45

    def _generate_tag_and_justification(self, posicao, preco, media_bruta, xp, upside, sg_prob_pct, is_home, opp_abrev, opp_pos, scout, jogos):
        """Gera tag inteligente e justificativa objetiva em texto claro para cada atleta."""
        loc_str = "Mandante" if is_home else "Visitante"
        num_j = max(1, jogos)
        
        # 1. Defensores (Goleiro, Lateral, Zagueiro)
        if posicao in ['Goleiro', 'Lateral', 'Zagueiro']:
            if (sg_prob_pct >= 55.0 and xp >= 6.0) or (xp >= 7.5):
                tag = "Excelente"
                tag_color = "#10b981"
                status_cons = "MANTER"
                just = f"{loc_str} com alta chance de SG ({sg_prob_pct:.0f}%) contra o {opp_abrev}."
                if scout.get('DS', 0) / num_j >= 2.0:
                    just += " Excelente volume de desarmes."
            elif xp >= 5.0 or (sg_prob_pct >= 45.0 and preco <= 8.5):
                tag = "Boa Opção"
                tag_color = "#f59e0b"
                status_cons = "MANTER"
                just = f"{loc_str} contra {opp_abrev} ({opp_pos}º); chance moderada de SG ({sg_prob_pct:.0f}%)."
            elif upside >= 8.5 and preco <= 7.0:
                tag = "Aposta"
                tag_color = "#8b5cf6"
                status_cons = "ATENCAO"
                just = f"Preço atrativo (C$ {preco:.2f}) e bom teto de pontos ({upside:.2f} pts), com risco de SG ({sg_prob_pct:.0f}%)."
            else:
                tag = "Evitar"
                tag_color = "#ef4444"
                status_cons = "TROCAR"
                just = f"{loc_str} com baixa probabilidade de SG ({sg_prob_pct:.0f}%); custo-benefício desfavorável para a rodada."

        # 2. Meias e Atacantes
        elif posicao in ['Meia', 'Atacante']:
            if xp >= 7.5 or (xp >= 6.5 and is_home and opp_pos >= 12):
                tag = "Excelente"
                tag_color = "#10b981"
                status_cons = "MANTER"
                if is_home:
                    just = f"Mandante contra a defesa vulnerável do {opp_abrev} ({opp_pos}º) com alto potencial ofensivo ({xp:.2f} xP)."
                else:
                    just = f"Grande fase individual com média projetada alta ({xp:.2f} xP) e teto de {upside:.2f} pts."
            elif xp >= 5.5 or (upside >= 9.5 and is_home):
                tag = "Boa Opção"
                tag_color = "#f59e0b"
                status_cons = "MANTER"
                just = f"Confronto favorável ({'em casa' if is_home else 'fora'}) contra {opp_abrev}; boa regularidade ofensiva."
            elif upside >= 9.0 and preco <= 8.5:
                tag = "Aposta"
                tag_color = "#8b5cf6"
                status_cons = "ATENCAO"
                just = f"Jogador agudo com teto elevado ({upside:.2f} pts) e bom preço, mas oscila na pontuação básica."
            else:
                tag = "Evitar"
                tag_color = "#ef4444"
                status_cons = "TROCAR"
                if not is_home:
                    just = f"Visitante contra o {opp_abrev}; projeção baixa ({xp:.2f} xP) para o custo de C$ {preco:.2f}."
                else:
                    just = f"Baixo volume de scouts decisivos recentes; retorno projetado insuficiente para o preço."

        # 3. Técnico
        else:
            tag = "Boa Opção"
            tag_color = "#f59e0b"
            status_cons = "MANTER"
            just = f"Comanda equipe {loc_str.lower()} em duelo contra {opp_abrev}."

        return tag, tag_color, status_cons, just
