import argparse
import sys
from rich.console import Console

from cartola_bot.api import CartolaAPI
from cartola_bot.scoring import Scorer
from cartola_bot.solver import TeamOptimizer
from cartola_bot.exporter import Exporter
from cartola_bot.utils.config_loader import load_config

def main():
    console = Console()
    
    # Carregar Configuração
    try:
        config = load_config()
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar configuração:[/bold red] {e}")
        sys.exit(1)

    defaults = config.get('defaults', {})
    available_formations = list(config.get('formations', {}).keys())
    
    # Argumentos CLI
    parser = argparse.ArgumentParser(description="Cartola FC Optimizer - Maximizador de Pontos")
    parser.add_argument("-b", "--budget", type=float, default=None, 
                        help=f"Orçamento total em cartoletas (padrão: {defaults.get('budget', 146.07)})")
    parser.add_argument("-f", "--formation", type=str, default=None, 
                        choices=available_formations + ["auto"],
                        help=f"Formação tática específica ou 'auto' para encontrar a melhor (padrão: {defaults.get('formation', 'auto')})")
    parser.add_argument("--max-per-club", type=int, default=defaults.get('max_players_per_club', 5),
                        help=f"Máximo de atletas do mesmo clube no time (padrão: {defaults.get('max_players_per_club', 5)})")
    parser.add_argument("--no-cache", action="store_false", dest="use_cache", 
                        help="Desativar uso de cache para dados da API")
    args = parser.parse_args()

    # Se não foram passados argumentos via terminal, faz perguntas interativas super legíveis
    from rich.prompt import Prompt, FloatPrompt
    
    if args.budget is None:
        default_b = float(defaults.get('budget', 146.07))
        console.print(f"\n[bold cyan]💰 SALDO DA CARTEIRA:[/bold cyan] Quanto você tem em cartoletas?")
        args.budget = FloatPrompt.ask(
            f" [green]Digite o valor (pressione Enter para {default_b:.2f})[/green]",
            default=default_b
        )
        
    if args.formation is None:
        default_f = defaults.get('formation', 'auto')
        console.print(f"\n[bold cyan]📋 FORMAÇÃO TÁTICA:[/bold cyan] 'auto' (escolhe a melhor) ou 4-3-3, 3-4-3, 4-4-2, 3-5-2, 5-3-2")
        args.formation = Prompt.ask(
            f" [green]Escolha a formação (pressione Enter para '{default_f}')[/green]",
            choices=available_formations + ["auto"],
            default=default_f
        )
        console.print()

    # Inicializar Componentes
    api = CartolaAPI(config)
    scorer = Scorer(config)
    optimizer = TeamOptimizer(config)
    exporter = Exporter()

    console.print("[bold yellow]Buscando e processando dados do Cartola FC...[/bold yellow]")
    
    try:
        mercado_data = api.get_mercado(use_cache=args.use_cache)
        partidas_data = api.get_partidas(use_cache=args.use_cache)
        
        df = scorer.process_data(mercado_data, partidas_data)
        
        if df.empty:
            console.print("[bold red]Erro: Nenhum jogador provável encontrado.[/bold red]")
            return

        all_formations_summary = None
        
        if args.formation == "auto":
            console.print(f"Buscando a [bold green]formação tática ideal[/bold green] para o orçamento de [bold]C$ {args.budget:.2f}[/bold]...")
            chosen_formation, selected_df, best_score, all_formations_summary = optimizer.optimize_best_formation(
                df, budget=args.budget, max_players_per_club=args.max_per_club
            )
        else:
            chosen_formation = args.formation
            console.print(f"Calculando o melhor time para [bold]C$ {args.budget:.2f}[/bold] (Formação fixa: {chosen_formation})...")
            selected_df = optimizer.optimize(
                df, budget=args.budget, formation_name=chosen_formation, max_players_per_club=args.max_per_club
            )
        
        if selected_df is not None and not selected_df.empty:
            reservas = optimizer.get_reservas(df, selected_df)
            
            # Exibir no Console
            exporter.print_to_console(
                selected_df, reservas, args.budget, 
                formation=chosen_formation, 
                all_formations_summary=all_formations_summary
            )
            
            # Exportar Arquivos
            csv_path, img_path = exporter.export_files(
                selected_df, reservas, args.budget, formation=chosen_formation
            )
            
            console.print(f"\n[bold green]✅ Escalação otimizada com sucesso![/bold green]")
            console.print(f"📄 CSV: [dim]{csv_path}[/dim]")
            console.print(f"🖼️ Imagem: [dim]{img_path}[/dim]")
        else:
            console.print("[bold red]Não foi possível montar um time completo com esse orçamento e formação.[/bold red]")
            console.print("[dim]Dica: Tente aumentar o orçamento ou usar '--formation auto'.[/dim]")

    except Exception as e:
        console.print(f"[bold red]Ocorreu um erro inesperado:[/bold red] {e}")
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    main()

