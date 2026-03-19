#!/usr/bin/env python3
"""
Script para gerar relatório de contribuições dos alunos.
Analisa commits, issues, PRs e gera visualizações automáticas.
"""

import os
import subprocess
import json
from datetime import datetime, timedelta
from collections import defaultdict
import re

try:
    from github import Github
    import matplotlib.pyplot as plt
    import pandas as pd
    from tabulate import tabulate
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False
    print("⚠️  Dependências não instaladas. Usando modo simplificado.")


def get_git_contributors():
    """Obtém lista de contribuidores do repositório."""
    cmd = ['git', 'log', '--format=%aN|%aE', '--all']
    result = subprocess.run(cmd, capture_output=True, text=True)

    contributors = {}
    for line in result.stdout.strip().split('\n'):
        if '|' in line:
            name, email = line.split('|')
            if email not in contributors:
                contributors[email] = name

    return contributors


def get_weekly_commits(weeks_back=24):
    """Analisa commits por autor nas últimas N semanas (padrão: 24 semanas = 1 semestre)."""
    today = datetime.now()
    weekly_data = defaultdict(lambda: defaultdict(int))

    for week in range(weeks_back):
        week_start = today - timedelta(weeks=week+1)
        week_end = today - timedelta(weeks=week)

        week_label = week_start.strftime('%Y-%m-%d')

        cmd = [
            'git', 'log',
            f'--since={week_start.strftime("%Y-%m-%d")}',
            f'--until={week_end.strftime("%Y-%m-%d")}',
            '--format=%aN',
            '--all'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        commits = result.stdout.strip().split('\n')

        for author in commits:
            if author:
                weekly_data[week_label][author] += 1

    return weekly_data


def get_commit_stats_by_author():
    """Obtém estatísticas detalhadas de commits por autor."""
    cmd = ['git', 'log', '--format=%aN', '--numstat', '--all']
    result = subprocess.run(cmd, capture_output=True, text=True)

    stats = defaultdict(lambda: {'commits': 0, 'additions': 0, 'deletions': 0, 'files': set()})
    current_author = None

    for line in result.stdout.split('\n'):
        if line and not '\t' in line:
            current_author = line.strip()
            stats[current_author]['commits'] += 1
        elif '\t' in line and current_author:
            parts = line.split('\t')
            if len(parts) >= 3:
                try:
                    additions = int(parts[0]) if parts[0] != '-' else 0
                    deletions = int(parts[1]) if parts[1] != '-' else 0
                    filename = parts[2]

                    stats[current_author]['additions'] += additions
                    stats[current_author]['deletions'] += deletions
                    stats[current_author]['files'].add(filename)
                except ValueError:
                    pass

    # Converter sets para contagem
    for author in stats:
        stats[author]['files'] = len(stats[author]['files'])

    return dict(stats)


def get_documentation_contributions():
    """Analisa contribuições em arquivos de documentação."""
    docs_pattern = r'\.(md|txt)$'

    cmd = ['git', 'log', '--format=%aN', '--name-only', '--all', '--', 'documentos/', 'README.md']
    result = subprocess.run(cmd, capture_output=True, text=True)

    doc_commits = defaultdict(lambda: {'docs_commits': 0, 'docs_files': set()})
    current_author = None

    for line in result.stdout.split('\n'):
        line = line.strip()
        if line and not '/' in line and not '.' in line:
            current_author = line
            doc_commits[current_author]['docs_commits'] += 1
        elif line and current_author and re.search(docs_pattern, line):
            doc_commits[current_author]['docs_files'].add(line)

    for author in doc_commits:
        doc_commits[author]['docs_files'] = len(doc_commits[author]['docs_files'])

    return dict(doc_commits)


def generate_markdown_report(stats, weekly_data, doc_stats):
    """Gera relatório em formato Markdown."""
    report = []
    report.append("# 📊 Relatório de Contribuições do Projeto\n")
    report.append(f"**Última atualização:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
    report.append("---\n")

    # Resumo geral
    report.append("## 📈 Resumo Geral de Contribuições\n")

    table_data = []
    for author in sorted(stats.keys()):
        author_stats = stats[author]
        author_docs = doc_stats.get(author, {})

        table_data.append([
            author,
            author_stats['commits'],
            author_stats['additions'],
            author_stats['deletions'],
            author_stats['files'],
            author_docs.get('docs_commits', 0),
            author_docs.get('docs_files', 0)
        ])

    headers = ['Aluno', 'Commits', 'Linhas+', 'Linhas-', 'Arquivos', 'Docs Commits', 'Docs Arquivos']

    if DEPS_AVAILABLE:
        report.append(tabulate(table_data, headers=headers, tablefmt='github'))
    else:
        # Formato markdown simples
        report.append('| ' + ' | '.join(headers) + ' |')
        report.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
        for row in table_data:
            report.append('| ' + ' | '.join(str(cell) for cell in row) + ' |')

    report.append("\n")

    # Contribuições semanais
    report.append("## 📅 Contribuições Semanais (Todo o Semestre)\n")

    # Organizar dados semanais
    weeks = sorted(weekly_data.keys(), reverse=True)
    all_authors = set()
    for week_data in weekly_data.values():
        all_authors.update(week_data.keys())

    weekly_table = []
    for week in weeks:
        week_commits = weekly_data[week]
        row = [week]
        for author in sorted(all_authors):
            commits = week_commits.get(author, 0)
            if commits > 0:
                row.append(f"{author}: {commits}")
        weekly_table.append(row)

    for row in weekly_table:
        if len(row) > 1:
            report.append(f"**{row[0]}**: {', '.join(row[1:])}\n")
        else:
            report.append(f"**{row[0]}**: Sem commits\n")

    report.append("\n")

    # Gráfico (se disponível)
    if os.path.exists('documentos/img/contribution-weekly.png'):
        report.append("## 📊 Visualização Gráfica\n")
        report.append("![Contribuições Semanais](img/contribution-weekly.png)\n")
        report.append("\n")

    # Observações
    report.append("## ℹ️ Observações\n")
    report.append("- **Commits**: Número total de commits realizados\n")
    report.append("- **Linhas+**: Linhas de código adicionadas\n")
    report.append("- **Linhas-**: Linhas de código removidas\n")
    report.append("- **Arquivos**: Número de arquivos únicos modificados\n")
    report.append("- **Docs Commits**: Commits em arquivos de documentação\n")
    report.append("- **Docs Arquivos**: Arquivos de documentação modificados\n")
    report.append("\n---\n")
    report.append("*Relatório gerado automaticamente via GitHub Actions*\n")

    return '\n'.join(report)


def generate_visualization(weekly_data, stats):
    """Gera gráficos de contribuição."""
    if not DEPS_AVAILABLE:
        print("⚠️  Matplotlib não disponível. Pulando geração de gráficos.")
        return

    # Criar diretório se não existir
    os.makedirs('documentos/img', exist_ok=True)

    # Preparar dados para o gráfico
    weeks = sorted(weekly_data.keys())
    all_authors = set()
    for week_data in weekly_data.values():
        all_authors.update(week_data.keys())

    all_authors = sorted(all_authors)

    # Criar matriz de dados
    data = []
    for author in all_authors:
        author_data = [weekly_data[week].get(author, 0) for week in weeks]
        data.append(author_data)

    # Gráfico de linha
    plt.figure(figsize=(14, 7))

    for i, author in enumerate(all_authors):
        plt.plot(weeks, data[i], marker='o', label=author, linewidth=2)

    plt.xlabel('Semana', fontsize=12)
    plt.ylabel('Número de Commits', fontsize=12)
    plt.title('Contribuições Semanais por Aluno', fontsize=14, fontweight='bold')
    plt.legend(loc='best')
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    plt.savefig('documentos/img/contribution-weekly.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Gráfico de pizza para commits totais
    total_commits = [(author, stats[author]['commits']) for author in stats]
    total_commits.sort(key=lambda x: x[1], reverse=True)

    if total_commits:
        plt.figure(figsize=(10, 10))
        authors = [item[0] for item in total_commits]
        commits = [item[1] for item in total_commits]

        plt.pie(commits, labels=authors, autopct='%1.1f%%', startangle=90)
        plt.title('Distribuição Total de Commits', fontsize=14, fontweight='bold')
        plt.axis('equal')

        plt.savefig('documentos/img/contribution-total.png', dpi=150, bbox_inches='tight')
        plt.close()

    print("✅ Gráficos gerados com sucesso!")


def main():
    """Função principal."""
    print("🔍 Analisando contribuições do repositório...\n")

    # Obter dados
    contributors = get_git_contributors()
    print(f"📋 Contribuidores encontrados: {len(contributors)}")

    stats = get_commit_stats_by_author()
    print(f"📊 Estatísticas coletadas para {len(stats)} autores")

    weekly_data = get_weekly_commits(weeks_back=24)  # 24 semanas = 1 semestre completo
    print(f"📅 Dados semanais coletados para {len(weekly_data)} semanas")

    doc_stats = get_documentation_contributions()
    print(f"📝 Contribuições em documentação analisadas")

    # Gerar visualizações
    print("\n📊 Gerando visualizações...")
    generate_visualization(weekly_data, stats)

    # Gerar relatório
    print("📄 Gerando relatório Markdown...")
    report = generate_markdown_report(stats, weekly_data, doc_stats)

    # Salvar relatório
    with open('documentos/CONTRIBUTION_REPORT.md', 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✅ Relatório salvo em: documentos/CONTRIBUTION_REPORT.md")
    print("✅ Processo concluído com sucesso!")


if __name__ == '__main__':
    main()
