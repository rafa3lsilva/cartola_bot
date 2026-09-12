import json
import os
import pandas as pd
from datetime import datetime

OFFICIAL_FILE = "time_oficial_ativo.json"
HISTORICO_DIR = "historico"

def is_gsheets_configured():
    """Verifica se as credenciais do Google Sheets estão configuradas no Streamlit Secrets."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            return True
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            return True
    except Exception:
        pass
    return False

def get_gsheets_connection():
    """Retorna a conexão GSheetsConnection do Streamlit."""
    try:
        import streamlit as st
        from streamlit_gsheets import GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn
    except Exception as e:
        return None

def load_official_team(rodada=None):
    """
    Carrega os dados do time oficial escalado.
    Tenta primeiro o Google Sheets (se configurado), com fallback para arquivos JSON locais.
    """
    # 1. Tentar ler do Google Sheets
    if is_gsheets_configured():
        try:
            conn = get_gsheets_connection()
            if conn:
                df_hist = conn.read(worksheet="historico_rodadas", ttl=5)
                if df_hist is not None and not df_hist.empty:
                    if rodada is not None:
                        df_target = df_hist[df_hist["rodada"].astype(str) == str(rodada)]
                    else:
                        df_target = df_hist.sort_values(by="rodada", ascending=False).head(1)
                        
                    if not df_target.empty and "snapshot_json" in df_target.columns:
                        json_str = df_target.iloc[0]["snapshot_json"]
                        return json.loads(json_str)
        except Exception:
            pass

    # 2. Fallback: Arquivos JSON locais
    if rodada is not None:
        hist_path = os.path.join(HISTORICO_DIR, f"rodada_{rodada}.json")
        if os.path.exists(hist_path):
            try:
                with open(hist_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
                
    if os.path.exists(OFFICIAL_FILE):
        try:
            with open(OFFICIAL_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    # Default fallback
    return {
        "rodada": 25,
        "starters_ids": [91101, 107093, 105531, 91772, 123445, 117632, 87747, 104783, 143193, 118844, 113103, 97341],
        "captain_id": 143193,
        "reserves_ids": {'Goleiro': 71631, 'Lateral': 91706, 'Zagueiro': 130307, 'Meia': 84626, 'Atacante': 114208},
        "super_sub_pos": "Atacante"
    }

def get_saved_rounds():
    """Retorna lista de todas as rodadas salvas (Google Sheets + JSON local)."""
    rounds = set()
    
    # 1. Google Sheets
    if is_gsheets_configured():
        try:
            conn = get_gsheets_connection()
            if conn:
                df_hist = conn.read(worksheet="historico_rodadas", ttl=5)
                if df_hist is not None and not df_hist.empty and "rodada" in df_hist.columns:
                    for r in df_hist["rodada"].dropna():
                        rounds.add(int(r))
        except Exception:
            pass

    # 2. Local
    os.makedirs(HISTORICO_DIR, exist_ok=True)
    if os.path.exists(OFFICIAL_FILE):
        try:
            with open(OFFICIAL_FILE, 'r', encoding='utf-8') as f:
                d = json.load(f)
                if 'rodada' in d:
                    rounds.add(int(d['rodada']))
        except Exception:
            pass
            
    for f in os.listdir(HISTORICO_DIR):
        if f.startswith("rodada_") and f.endswith(".json"):
            try:
                r_num = int(f.replace("rodada_", "").replace(".json", ""))
                rounds.add(r_num)
            except Exception:
                pass
                
    return sorted(list(rounds), reverse=True)

def save_official_team(rodada, starters_df, captain_id, reserves_dict, super_sub_pos="Atacante"):
    """
    Salva um snapshot completo e imutável da escalação oficial.
    Grava localmente (JSON) e sincroniza na planilha Google Sheets (se configurada).
    """
    os.makedirs(HISTORICO_DIR, exist_ok=True)
    
    starters_list = []
    starters_names = []
    for _, row in starters_df.iterrows():
        p_id = int(row['ID'])
        is_cap = (p_id == int(captain_id))
        nome = str(row['Nome'])
        pos = str(row['Posicao'])
        starters_names.append(f"{nome} ({pos}){' [C]' if is_cap else ''}")
        starters_list.append({
            'ID': p_id,
            'Nome': nome,
            'Posicao': pos,
            'Clube': str(row['Clube']),
            'Preco': float(row['Preco']),
            'Media': float(row.get('Media', row['Media_Ajustada'])),
            'Min_Val': float(row.get('Min_Val', row['Preco'] * 0.37)),
            'Media_Ajustada': float(row['Media_Ajustada']),
            'Upside': float(row.get('Upside', row['Media_Ajustada'])),
            'SG_Prob': float(row['SG_Prob']) if pd.notna(row.get('SG_Prob')) else None,
            'Confronto': str(row.get('Confronto', '')),
            'Is_Capitao': is_cap,
            'Foto': str(row.get('Foto', '')),
            'Escudo': str(row.get('Escudo', ''))
        })

    reserves_data = {}
    for pos, r in reserves_dict.items():
        is_super = (pos == super_sub_pos)
        reserves_data[pos] = {
            'ID': int(r['ID']),
            'Nome': str(r['Nome']),
            'Posicao': str(r['Posicao']),
            'Clube': str(r['Clube']),
            'Preco': float(r['Preco']),
            'Media_Ajustada': float(r.get('Media_Ajustada', 0.0)),
            'Upside': float(r.get('Upside', r.get('Media_Ajustada', 0.0))),
            'Is_Super_Sub': is_super,
            'Foto': str(r.get('Foto', '')),
            'Escudo': str(r.get('Escudo', ''))
        }

    total_cost = float(starters_df['Preco'].sum())
    cap_bonus = float(starters_df[starters_df['ID'] == int(captain_id)]['Media_Ajustada'].iloc[0] * 0.5) if not starters_df[starters_df['ID'] == int(captain_id)].empty else 0.0
    total_xp = round(float(starters_df['Media_Ajustada'].sum() + cap_bonus), 2)

    data = {
        "rodada": int(rodada),
        "saved_at": datetime.now().isoformat(),
        "total_cost": total_cost,
        "total_xp_projected": total_xp,
        "captain_id": int(captain_id),
        "super_sub_pos": super_sub_pos,
        "starters_ids": [int(i) for i in starters_df['ID'].tolist()],
        "reserves_ids": {pos: int(r['ID']) for pos, r in reserves_dict.items()},
        "starters": starters_list,
        "reserves": reserves_data
    }

    # 1. Salvar localmente
    with open(OFFICIAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    hist_file = os.path.join(HISTORICO_DIR, f"rodada_{rodada}.json")
    with open(hist_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # 2. Sincronizar com Google Sheets
    if is_gsheets_configured():
        try:
            conn = get_gsheets_connection()
            if conn:
                snapshot_json = json.dumps(data, ensure_ascii=False)
                
                row_summary = {
                    "rodada": int(rodada),
                    "salvo_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "custo_total": total_cost,
                    "projecao_xp": total_xp,
                    "capitao_id": int(captain_id),
                    "super_sub": super_sub_pos,
                    "titulares": ", ".join(starters_names),
                    "snapshot_json": snapshot_json
                }
                
                df_ativo = pd.DataFrame([row_summary])
                
                try:
                    df_hist = conn.read(worksheet="historico_rodadas", ttl=0)
                    if df_hist is not None and not df_hist.empty and "rodada" in df_hist.columns:
                        df_hist = df_hist[df_hist["rodada"].astype(str) != str(rodada)]
                        df_hist = pd.concat([df_hist, df_ativo], ignore_index=True)
                    else:
                        df_hist = df_ativo
                    conn.update(worksheet="historico_rodadas", data=df_hist)
                except Exception:
                    conn.update(worksheet="historico_rodadas", data=df_ativo)
        except Exception as e:
            print(f"[Aviso] Erro ao sincronizar com Google Sheets: {e}")

    return data

def load_auth_session():
    """Carrega a sessão salva da planilha do Google Sheets (aba sessao_cartola) ou cache local."""
    if is_gsheets_configured():
        try:
            conn = get_gsheets_connection()
            if conn:
                df_sess = conn.read(worksheet="sessao_cartola", ttl=2)
                if df_sess is not None and not df_sess.empty:
                    row = df_sess.iloc[0].to_dict()
                    return row
        except Exception:
            pass
    return None

def save_auth_session(session_dict):
    """Salva a sessão na planilha do Google Sheets (aba sessao_cartola)."""
    if is_gsheets_configured():
        try:
            conn = get_gsheets_connection()
            if conn:
                df_save = pd.DataFrame([session_dict])
                conn.update(worksheet="sessao_cartola", data=df_save)
        except Exception as e:
            print(f"[Aviso] Erro ao salvar sessão no Google Sheets: {e}")

def clear_auth_session():
    """Limpa a sessão salva na planilha do Google Sheets."""
    if is_gsheets_configured():
        try:
            conn = get_gsheets_connection()
            if conn:
                empty_df = pd.DataFrame(columns=["token", "email", "glbid", "authenticated_at", "team_name"])
                conn.update(worksheet="sessao_cartola", data=empty_df)
        except Exception:
            pass

