import argparse, asyncio, sys, time, httpx, json, csv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TaskProgressColumn
from .core import Raider
from .utils import VERSION, get_tld_extractor

console = Console()
_silent = False

def cprint(*args, **kwargs):
    if not _silent:
        console.print(*args, **kwargs)

def format_result(result):
    coverage = result.get("coverage", {})
    return f"[[{result['color']}][bold]{result['score']:06.2f}[/bold][/]] [bold cyan]{result['domain']}[/] -> [bold {result['color']}]{result['tier']}[/]"

def export_results(results, output_path):
    ext = output_path.lower().split('.')[-1] if '.' in output_path else 'txt'
    
    try:
        if ext == 'json':
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
        elif ext == 'csv':
            fieldnames = ["domain", "score", "tier", "confidence", "providers_available", "providers_total", "provider_coverage_ratio", "weight_covered", "weight_total", "weight_coverage_ratio"]
            with open(output_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in results:
                    coverage = r.get("coverage", {})
                    writer.writerow({
                        "domain": r.get("domain"),
                        "score": r.get("score"),
                        "tier": r.get("tier"),
                        "confidence": r.get("confidence"),
                        "providers_available": coverage.get("providers_available"),
                        "providers_total": coverage.get("providers_total"),
                        "provider_coverage_ratio": coverage.get("providers_ratio"),
                        "weight_covered": coverage.get("weight_covered"),
                        "weight_total": coverage.get("weight_total"),
                        "weight_coverage_ratio": coverage.get("weight_ratio"),
                    })
        else:
            with open(output_path, 'w') as f:
                for r in results:
                    coverage = r.get("coverage", {})
                    f.write(f"{r.get('domain')},{r.get('score')},{r.get('tier')},{r.get('confidence')},{coverage.get('providers_available')}/{coverage.get('providers_total')}\n")
        
        cprint(f"[dim]Results saved to [cyan]{output_path}[/][/]")
    except OSError as e:
        cprint(f"[red]Error:[/] Could not write to {output_path}: {e}")

def open_output_stream(output_path):
    ext = output_path.lower().split('.')[-1] if '.' in output_path else 'txt'
    try:
        if ext == 'json':
            f = open(output_path, 'w')
            f.write("[\n")
            f.flush()
            return {"ext": ext, "file": f, "first": True, "path": output_path}
        if ext == 'csv':
            f = open(output_path, 'w', newline='')
            fieldnames = ["domain", "score", "tier", "confidence", "providers_available", "providers_total", "provider_coverage_ratio", "weight_covered", "weight_total", "weight_coverage_ratio"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            f.flush()
            return {"ext": ext, "file": f, "writer": writer, "path": output_path}

        f = open(output_path, 'w')
        return {"ext": ext, "file": f, "path": output_path}
    except OSError as e:
        cprint(f"[red]Error:[/] Could not write to {output_path}: {e}")
        return None

def write_output_stream(stream, result):
    if not stream:
        return

    f = stream["file"]
    ext = stream["ext"]

    try:
        if ext == 'json':
            if not stream["first"]:
                f.write(",\n")
            f.write(json.dumps(result, indent=2, default=str))
            stream["first"] = False
        elif ext == 'csv':
            coverage = result.get("coverage", {})
            stream["writer"].writerow({
                "domain": result.get("domain"),
                "score": result.get("score"),
                "tier": result.get("tier"),
                "confidence": result.get("confidence"),
                "providers_available": coverage.get("providers_available"),
                "providers_total": coverage.get("providers_total"),
                "provider_coverage_ratio": coverage.get("providers_ratio"),
                "weight_covered": coverage.get("weight_covered"),
                "weight_total": coverage.get("weight_total"),
                "weight_coverage_ratio": coverage.get("weight_ratio"),
            })
        else:
            coverage = result.get("coverage", {})
            f.write(f"{result.get('domain')},{result.get('score')},{result.get('tier')},{result.get('confidence')},{coverage.get('providers_available')}/{coverage.get('providers_total')}\n")
        f.flush()
    except OSError as e:
        cprint(f"[red]Error:[/] Could not write to {stream['path']}: {e}")

def close_output_stream(stream):
    if not stream:
        return
    try:
        if stream["ext"] == 'json':
            stream["file"].write("\n]\n")
        stream["file"].close()
        cprint(f"[dim]Results saved to [cyan]{stream['path']}[/][/]")
    except OSError as e:
        cprint(f"[red]Error:[/] Could not finalize {stream['path']}: {e}")

async def scan_domains(raider, domains, max_concurrent=10, output_stream=None):
    results = []
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def scan_with_semaphore(client, domain):
        async with semaphore:
            raw = await raider.analyze(client, domain)
            return raider.summarize(domain, raw)
            
    limits = httpx.Limits(max_keepalive_connections=max_concurrent, max_connections=max_concurrent * 2)
    async with httpx.AsyncClient(
        verify=False,
        follow_redirects=True,
        limits=limits,
        timeout=httpx.Timeout(15.0, connect=5.0)
    ) as client:
        tasks = [scan_with_semaphore(client, domain) for domain in domains]
        
        if _silent:
            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                write_output_stream(output_stream, result)
            return results
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=24),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("", total=len(domains))
            
            for coro in asyncio.as_completed(tasks):
                result = await coro
                progress.console.print(format_result(result))
                results.append(result)
                write_output_stream(output_stream, result)
                progress.advance(task)
                
    return results

def main():
    global _silent
    
    parser = argparse.ArgumentParser(description="Raider - Domain ranking and scoring tool")
    parser.add_argument("-d", "--domain", help="Domain to check")
    parser.add_argument("-l", "--list", help="List of domains to check")
    parser.add_argument("-o", "--output", help="Output file (.txt, .json, .csv)")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Number of concurrent threads")
    parser.add_argument("--json", action="store_true", help="Output results as JSON to stdout")
    args = parser.parse_args()

    _silent = args.json

    banner = rf"""[bold cyan]
    ▘ ▌    
▛▘▀▌▌▛▌█▌▛▘
▌ █▌▌▙▌▙▖▌  [/bold cyan][dim]v{VERSION}[/dim]
[white][dim]pajarori[/dim][/white]
"""

    domains = []
    
    if not sys.stdin.isatty():
        domains.extend([line.strip() for line in sys.stdin if line.strip()])

    if args.domain:
        domains.append(args.domain)
    elif args.list:
        try:
            with open(args.list, "r") as f:
                domains.extend([line.strip() for line in f if line.strip()])
        except OSError as e:
            cprint(f"[red]Error:[/] Could not read file: {e}")
            return
            
    seen = set()
    unique_domains = []
    extractor = get_tld_extractor()
    
    def get_root_domain(domain_str):
        ext = extractor(domain_str)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}"
        return domain_str
        
    for d in domains:
        root_d = get_root_domain(d)
        if root_d:
            root_d = root_d.lower()
        if root_d and root_d not in seen:
            seen.add(root_d)
            unique_domains.append(root_d)
            
    domains = unique_domains
    
    if not domains:
        cprint(banner)
        cprint("[red]No domains provided. Use -d, -l, or pipe input.[/]")
        return
        
    cprint(banner)
    cprint(f"[dim]Checking [cyan]{len(domains)}[/] domains[/]\n")
    
    raider = Raider()
    start_time = time.time()
    output_stream = None
    if args.output and not args.json:
        output_stream = open_output_stream(args.output)
    results = asyncio.run(scan_domains(raider, domains, max_concurrent=args.threads, output_stream=output_stream))
    close_output_stream(output_stream)
    
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    elif args.output and not output_stream:
        export_results(results, args.output)
    
    elapsed = time.time() - start_time
    cprint(f"\n[dim]Scan complete in {elapsed:.2f} seconds.[/]")

if __name__ == "__main__":
    main()
