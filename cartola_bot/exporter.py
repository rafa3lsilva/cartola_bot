import os
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from rich.console import Console
from rich.table import Table

class Exporter:
    """Classe responsável por exibir e exportar os dados do time selecionado."""
    def __init__(self, export_dir="exports"):
        self.export_dir = export_dir
        self.csv_dir = os.path.join(export_dir, "csv")
        self.img_dir = os.path.join(export_dir, "img")
        os.makedirs(self.csv_dir, exist_ok=True)
        os.makedirs(self.img_dir, exist_ok=True)
        self.console = Console()

    def print_to_console(self, selected_df, reservas, budget, formation="4-3-3", all_formations_summary=None):
        """Imprime a escalação formatada no terminal com detalhes estatísticos e capitão."""
        total_cost = selected_df['Preco'].sum()
        budget_left = budget - total_cost
        
        # Identificar o Capitão
        if 'Is_Capitao' in selected_df.columns and selected_df['Is_Capitao'].any():
            capitao_row = selected_df[selected_df['Is_Capitao']].iloc[0]
            capitao_nome = capitao_row['Nome']
            capitao_xp_extra = capitao_row['Media_Ajustada'] * 0.5
        else:
            jogadores = selected_df[selected_df['Posicao'] != 'Técnico']
            capitao_idx = jogadores['Media_Ajustada'].idxmax()
            capitao_nome = jogadores.loc[capitao_idx, 'Nome']
            capitao_xp_extra = jogadores.loc[capitao_idx, 'Media_Ajustada'] * 0.5
        
        total_xp = selected_df['Media_Ajustada'].sum() + capitao_xp_extra
        
        self.console.print(f"\n[bold green]💰 Orçamento Inicial:[/bold green] C$ {budget:.2f}")
        self.console.print(f"[bold green]💎 Custo Total (Titulares):[/bold green] C$ {total_cost:.2f}")
        self.console.print(f"[bold green]🏦 Sobrou no Caixa:[/bold green] C$ {budget_left:.2f}")
        self.console.print(f"[bold blue]🚀 Pontuação Esperada Total (xP c/ Capitão):[/bold blue] [bold yellow]{total_xp:.2f} pts[/bold yellow]")
        self.console.print(f"[bold cyan]📋 Formação Tática:[/bold cyan] {formation}\n")
        
        if all_formations_summary and len(all_formations_summary) > 1:
            comp_table = Table(title="Comparativo de Formações Táticas", show_header=True, header_style="bold blue")
            comp_table.add_column("Formação", style="bold")
            comp_table.add_column("xP Esperado", justify="right")
            comp_table.add_column("Custo", justify="right")
            comp_table.add_column("Status", justify="center")
            
            for f_name, data in sorted(all_formations_summary.items(), key=lambda x: x[1]['score'], reverse=True):
                is_chosen = "⭐ ESCOLHIDA" if f_name == formation else ""
                style = "bold green" if f_name == formation else "dim"
                comp_table.add_row(f_name, f"{data['score']:.2f} pts", f"C$ {data['cost']:.2f}", is_chosen, style=style)
            self.console.print(comp_table)
            self.console.print()
        
        table = Table(title=f"Escalação Ideal - {formation} (Com Capitão)", show_header=True, header_style="bold magenta")
        table.add_column("Posição", style="dim", width=10)
        table.add_column("Nome", style="bold cyan")
        table.add_column("Clube", justify="center")
        table.add_column("Preço", justify="right")
        table.add_column("Média Hist.", justify="right")
        table.add_column("Chance SG", justify="right")
        table.add_column("Mín. Val.", justify="right", style="dim")
        table.add_column("xP Esperado", justify="right")
        
        pos_order = ['Goleiro', 'Lateral', 'Zagueiro', 'Meia', 'Atacante', 'Técnico']
        
        for pos in pos_order:
            players = selected_df[selected_df['Posicao'] == pos]
            for _, p in players.iterrows():
                nome = p['Nome']
                media_bruta = f"{p['Media']:.2f}"
                xp_val = p['Media_Ajustada']
                xp_str = f"{xp_val:.2f}"
                sg_str = f"{p['SG_Prob']:.0f}%" if ('SG_Prob' in p and p['Posicao'] in ['Goleiro', 'Lateral', 'Zagueiro']) else "-"
                
                if nome == capitao_nome:
                    nome = f"👑 {nome} [C]"
                    xp_str = f"[bold yellow]{xp_val * 1.5:.2f} (x1.5)[/bold yellow]"
                    
                table.add_row(
                    p['Posicao'], nome, p['Clube'], f"{p['Preco']:.2f}", 
                    media_bruta, sg_str, f"{p['Min_Val']:.2f}", xp_str
                )
                
        self.console.print(table)
        
        if reservas:
            self.console.print("\n[bold yellow]🔄 BANCO DE RESERVAS DE LUXO (Troca Automática por Maior Pontuação)[/bold yellow]")
            res_table = Table(show_header=True, header_style="bold yellow")
            res_table.add_column("Posição", style="dim", width=10)
            res_table.add_column("Nome", style="bold cyan")
            res_table.add_column("Clube", justify="center")
            res_table.add_column("Preço", justify="right")
            res_table.add_column("Média Hist.", justify="right")
            res_table.add_column("xP Esperado", justify="right")
            res_table.add_column("Teto (Upside)", justify="right", style="bold green")
            res_table.add_column("Potencial de Troca", justify="center")
            
            custo_reservas = 0
            total_expected_gain = 0
            for pos in ['Goleiro', 'Lateral', 'Zagueiro', 'Meia', 'Atacante']:
                if pos in reservas:
                    r = reservas[pos]
                    custo_reservas += r['Preco']
                    gain = r.get('Expected_Gain', 0)
                    total_expected_gain += gain
                    upside_str = f"{r.get('Upside', r['Media_Ajustada']):.2f}"
                    gain_str = f"[green]+{gain:.2f} pts[/green]" if gain > 0 else "[dim]Segurança[/dim]"
                    
                    res_table.add_row(
                        r['Posicao'], r['Nome'], r['Clube'], f"{r['Preco']:.2f}", 
                        f"{r['Media']:.2f}", f"{r['Media_Ajustada']:.2f}",
                        upside_str, gain_str
                    )
            self.console.print(res_table)
            self.console.print(f"[dim]Custo total para todos os reservas: C$ {custo_reservas:.2f} | Ganho adicional estimado c/ trocas: +{total_expected_gain:.2f} pts[/dim]")

    def export_files(self, selected_df, reservas, budget, formation="4-3-3"):
        """Exporta o time para CSV e gera uma imagem gráfica da tabela."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Preparar DataFrame para exportação
        export_list = []
        
        # Identificar Capitão
        if 'Is_Capitao' in selected_df.columns and selected_df['Is_Capitao'].any():
            capitao_nome = selected_df[selected_df['Is_Capitao']].iloc[0]['Nome']
        else:
            jogadores = selected_df[selected_df['Posicao'] != 'Técnico']
            capitao_nome = jogadores.loc[jogadores['Media_Ajustada'].idxmax(), 'Nome'] if not jogadores.empty else ""
            
        for _, p in selected_df.iterrows():
            is_capitao = p['Nome'] == capitao_nome
            xp_final = round(p['Media_Ajustada'] * 1.5, 2) if is_capitao else p['Media_Ajustada']
            export_list.append({
                'Status': 'Titular',
                'Posicao': p['Posicao'],
                'Nome': f"{p['Nome']} [C]" if is_capitao else p['Nome'],
                'Clube': p['Clube'],
                'Preco': p['Preco'],
                'Min_Val': p['Min_Val'],
                'xP_Esperado': xp_final
            })
            
        if reservas:
            for pos, r in reservas.items():
                export_list.append({
                    'Status': 'Reserva',
                    'Posicao': r['Posicao'],
                    'Nome': r['Nome'],
                    'Clube': r['Clube'],
                    'Preco': r['Preco'],
                    'Min_Val': r['Min_Val'],
                    'xP_Esperado': r['Media_Ajustada']
                })
                
        export_df = pd.DataFrame(export_list)
        csv_path = os.path.join(self.csv_dir, f"time_{timestamp}_{formation}_b{budget}.csv")
        export_df.to_csv(csv_path, index=False, encoding='utf-8')
        
        # 2. Exportar Imagem
        fig, ax = plt.subplots(figsize=(10, len(export_df) * 0.45 + 1.2))
        ax.axis('tight')
        ax.axis('off')
        
        table_data = []
        for _, row in export_df.iterrows():
            table_data.append([
                row['Status'], row['Posicao'], row['Nome'], 
                row['Clube'], f"C$ {row['Preco']:.2f}", 
                f"{row['Min_Val']:.2f}", f"{row['xP_Esperado']:.2f}"
            ])
            
        columns = ('Status', 'Posição', 'Nome', 'Clube', 'Preço', 'Mín. Val.', 'xP Esperado')
        table = ax.table(cellText=table_data, colLabels=columns, cellLoc='center', loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 1.5)
        
        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_text_props(weight='bold', color='white')
                cell.set_facecolor('#2b5b84')
            elif row <= len(selected_df):
                if '[C]' in table_data[row-1][2]:
                    cell.set_facecolor('#fff2cc')
        
        plt.title(f"Cartola FC - Escalação Ideal ({formation}) | C$ {budget:.2f}", fontsize=12, weight='bold', pad=12)
        img_path = os.path.join(self.img_dir, f"time_{timestamp}_{formation}_b{budget}.png")
        plt.savefig(img_path, bbox_inches='tight', dpi=150)
        plt.close()
        
        return csv_path, img_path

