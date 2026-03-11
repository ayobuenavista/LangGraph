"""Tools available to the Front-end Agent."""

from __future__ import annotations

import json
import textwrap

from langchain_core.tools import tool


@tool
def scaffold_nextjs_component(
    component_name: str,
    component_type: str = "client",
    props: str = "{}",
) -> str:
    """Scaffold a Next.js component skeleton.

    Args:
        component_name: PascalCase component name.
        component_type: 'client' or 'server'.
        props: JSON string of prop name -> TypeScript type mappings.
    """
    prop_map: dict = json.loads(props) if props else {}
    directive = '"use client";\n\n' if component_type == "client" else ""

    prop_lines = []
    for name, ts_type in prop_map.items():
        prop_lines.append(f"  {name}: {ts_type};")

    interface_block = ""
    if prop_lines:
        interface_block = (
            f"interface {component_name}Props {{\n"
            + "\n".join(prop_lines)
            + "\n}\n\n"
        )

    params = f"{{ {', '.join(prop_map.keys())} }}: {component_name}Props" if prop_map else ""

    return textwrap.dedent(f"""\
        {directive}{interface_block}export default function {component_name}({params}) {{
          return (
            <div className="rounded-card bg-surface-800 p-4">
              {{/* {component_name} content */}}
            </div>
          );
        }}
    """)


@tool
def generate_chart_component(
    chart_type: str = "line",
    data_key: str = "value",
    x_key: str = "date",
    title: str = "Chart",
) -> str:
    """Generate a Recharts component for common chart types.

    Args:
        chart_type: 'line', 'bar', 'area', or 'pie'.
        data_key: The data field to plot on the Y axis.
        x_key: The data field for the X axis.
        title: Chart title displayed above the chart.
    """
    chart_map = {
        "line": ("LineChart", "Line"),
        "bar": ("BarChart", "Bar"),
        "area": ("AreaChart", "Area"),
    }

    if chart_type == "pie":
        return textwrap.dedent(f"""\
            "use client";

            import {{ PieChart, Pie, Cell, Tooltip, ResponsiveContainer }} from "recharts";

            interface DataPoint {{
              name: string;
              {data_key}: number;
            }}

            const COLORS = ["#6366F1", "#22D3EE", "#10B981", "#F59E0B", "#EF4444"];

            export default function {title.replace(" ", "")}Chart({{ data }}: {{ data: DataPoint[] }}) {{
              return (
                <div className="rounded-card bg-surface-800 p-4">
                  <h3 className="text-text-primary font-sans text-sm font-medium mb-3">
                    {title}
                  </h3>
                  <ResponsiveContainer width="100%" height={{300}}>
                    <PieChart>
                      <Pie data={{data}} dataKey="{data_key}" nameKey="name" cx="50%" cy="50%" outerRadius={{100}}>
                        {{data.map((_, i) => (
                          <Cell key={{i}} fill={{COLORS[i % COLORS.length]}} />
                        ))}}
                      </Pie>
                      <Tooltip
                        contentStyle={{{{ backgroundColor: "#1E293B", border: "none", borderRadius: "0.5rem" }}}}
                        labelStyle={{{{ color: "#F8FAFC" }}}}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              );
            }}
        """)

    container, element = chart_map.get(chart_type, chart_map["line"])

    return textwrap.dedent(f"""\
        "use client";

        import {{
          {container}, {element}, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
        }} from "recharts";

        interface DataPoint {{
          {x_key}: string;
          {data_key}: number;
        }}

        export default function {title.replace(" ", "")}Chart({{ data }}: {{ data: DataPoint[] }}) {{
          return (
            <div className="rounded-card bg-surface-800 p-4">
              <h3 className="text-text-primary font-sans text-sm font-medium mb-3">
                {title}
              </h3>
              <ResponsiveContainer width="100%" height={{300}}>
                <{container} data={{data}}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="{x_key}" tick={{{{ fill: "#94A3B8", fontSize: 12 }}}} />
                  <YAxis tick={{{{ fill: "#94A3B8", fontSize: 12 }}}} />
                  <Tooltip
                    contentStyle={{{{ backgroundColor: "#1E293B", border: "none", borderRadius: "0.5rem" }}}}
                    labelStyle={{{{ color: "#F8FAFC" }}}}
                  />
                  <{element}
                    type="monotone"
                    dataKey="{data_key}"
                    stroke="#6366F1"
                    fill="#6366F180"
                    strokeWidth={{2}}
                  />
                </{container}>
              </ResponsiveContainer>
            </div>
          );
        }}
    """)


@tool
def generate_data_fetcher(
    endpoint: str,
    hook_name: str = "useAppData",
    refresh_interval: int = 30000,
) -> str:
    """Generate a React data-fetching hook with SWR for real-time updates.

    Args:
        endpoint: The API endpoint path (e.g. '/api/prices').
        hook_name: Name for the custom hook.
        refresh_interval: Auto-refresh interval in milliseconds. Set to 0 for no polling.
    """
    swr_options = (
        f"refreshInterval: {refresh_interval},\n"
        f"              revalidateOnFocus: true,\n"
        f"              dedupingInterval: {refresh_interval // 2},"
    ) if refresh_interval > 0 else (
        "revalidateOnFocus: true,"
    )

    return textwrap.dedent(f"""\
        "use client";

        import useSWR from "swr";

        const fetcher = (url: string) => fetch(url).then((r) => r.json());

        export function {hook_name}() {{
          const {{ data, error, isLoading, mutate }} = useSWR(
            "{endpoint}",
            fetcher,
            {{
              {swr_options}
            }}
          );

          return {{
            data,
            isLoading,
            isError: !!error,
            refresh: mutate,
          }};
        }}
    """)


@tool
def scaffold_page_layout(
    page_name: str = "App",
    layout_type: str = "dashboard",
    sections: str = '["header", "content"]',
) -> str:
    """Generate a responsive page layout using Tailwind.

    Supports multiple layout types to match different project needs.

    Args:
        page_name: The page component name.
        layout_type: One of 'dashboard', 'marketing', 'app-shell', 'form', 'settings'.
            - dashboard: grid with metrics, charts, tables.
            - marketing: hero + feature sections + CTA.
            - app-shell: sidebar nav + main content area.
            - form: centered card with form steps.
            - settings: sidebar nav + stacked setting panels.
        sections: JSON array of section names.  Meaning varies by layout_type.
            dashboard sections: 'header', 'metrics', 'charts', 'table'
            marketing sections: 'hero', 'features', 'pricing', 'cta'
            app-shell sections: 'sidebar', 'topbar', 'content'
            form sections: 'header', 'steps', 'actions'
            settings sections: 'nav', 'profile', 'preferences', 'danger'
    """
    section_list: list[str] = json.loads(sections)

    if layout_type == "marketing":
        return _marketing_layout(page_name, section_list)
    elif layout_type == "app-shell":
        return _app_shell_layout(page_name, section_list)
    elif layout_type == "form":
        return _form_layout(page_name, section_list)
    elif layout_type == "settings":
        return _settings_layout(page_name, section_list)
    else:
        return _dashboard_layout(page_name, section_list)


def _dashboard_layout(page_name: str, sections: list[str]) -> str:
    section_jsx = []
    for section in sections:
        if section == "header":
            section_jsx.append(
                '        <header className="col-span-full flex items-center justify-between">\n'
                f'          <h1 className="text-2xl font-semibold text-text-primary">{page_name}</h1>\n'
                '          <div className="flex gap-2">{/* Filter controls */}</div>\n'
                '        </header>'
            )
        elif section == "metrics":
            section_jsx.append(
                '        <section className="col-span-full grid grid-cols-2 md:grid-cols-4 gap-4">\n'
                '          {/* MetricCard components */}\n'
                '        </section>'
            )
        elif section == "charts":
            section_jsx.append(
                '        <section className="col-span-full grid grid-cols-1 lg:grid-cols-2 gap-4">\n'
                '          {/* Chart components */}\n'
                '        </section>'
            )
        elif section == "table":
            section_jsx.append(
                '        <section className="col-span-full overflow-x-auto">\n'
                '          {/* DataTable component */}\n'
                '        </section>'
            )

    joined = "\n\n".join(section_jsx)
    return textwrap.dedent(f"""\
        import {{ Suspense }} from "react";

        export default function {page_name}Page() {{
          return (
            <main className="min-h-screen bg-surface-900 p-4 md:p-6 lg:p-8">
              <div className="mx-auto max-w-7xl grid gap-6">
        {joined}
              </div>
            </main>
          );
        }}
    """)


def _marketing_layout(page_name: str, sections: list[str]) -> str:
    section_jsx = []
    for section in sections:
        if section == "hero":
            section_jsx.append(
                '        <section className="flex flex-col items-center text-center py-20 px-4">\n'
                f'          <h1 className="text-5xl md:text-6xl font-bold text-text-primary mb-6">{page_name}</h1>\n'
                '          <p className="text-lg text-text-secondary max-w-2xl mb-8">{/* Subtitle */}</p>\n'
                '          <div className="flex gap-4">{/* CTA buttons */}</div>\n'
                '        </section>'
            )
        elif section == "features":
            section_jsx.append(
                '        <section className="grid grid-cols-1 md:grid-cols-3 gap-8 px-4 py-16 max-w-6xl mx-auto">\n'
                '          {/* FeatureCard components */}\n'
                '        </section>'
            )
        elif section == "pricing":
            section_jsx.append(
                '        <section className="py-16 px-4">\n'
                '          <h2 className="text-3xl font-bold text-text-primary text-center mb-12">Pricing</h2>\n'
                '          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">\n'
                '            {/* PricingCard components */}\n'
                '          </div>\n'
                '        </section>'
            )
        elif section == "cta":
            section_jsx.append(
                '        <section className="text-center py-20 px-4 bg-surface-800 rounded-2xl mx-4 mb-8">\n'
                '          <h2 className="text-3xl font-bold text-text-primary mb-4">Get Started</h2>\n'
                '          <p className="text-text-secondary mb-8">{/* CTA copy */}</p>\n'
                '          <button className="bg-primary-500 hover:bg-primary-600 text-white px-8 py-3 rounded-lg font-medium transition-colors">\n'
                '            {/* CTA label */}\n'
                '          </button>\n'
                '        </section>'
            )

    joined = "\n\n".join(section_jsx)
    return textwrap.dedent(f"""\
        export default function {page_name}Page() {{
          return (
            <main className="min-h-screen bg-surface-900">
        {joined}
            </main>
          );
        }}
    """)


def _app_shell_layout(page_name: str, sections: list[str]) -> str:
    has_sidebar = "sidebar" in sections
    has_topbar = "topbar" in sections

    sidebar_jsx = ""
    if has_sidebar:
        sidebar_jsx = (
            '        <aside className="hidden md:flex flex-col w-64 bg-surface-800 border-r border-surface-700 p-4">\n'
            '          <nav className="flex flex-col gap-1">{/* NavItem components */}</nav>\n'
            '        </aside>'
        )

    topbar_jsx = ""
    if has_topbar:
        topbar_jsx = (
            '          <header className="h-14 border-b border-surface-700 flex items-center justify-between px-4">\n'
            '            <div>{/* Breadcrumbs / Search */}</div>\n'
            '            <div className="flex items-center gap-3">{/* User menu */}</div>\n'
            '          </header>'
        )

    return textwrap.dedent(f"""\
        export default function {page_name}Layout({{ children }}: {{ children: React.ReactNode }}) {{
          return (
            <div className="min-h-screen bg-surface-900 flex">
        {sidebar_jsx}
              <div className="flex-1 flex flex-col">
        {topbar_jsx}
                <main className="flex-1 p-4 md:p-6 lg:p-8">
                  {{children}}
                </main>
              </div>
            </div>
          );
        }}
    """)


def _form_layout(page_name: str, sections: list[str]) -> str:
    return textwrap.dedent(f"""\
        "use client";

        export default function {page_name}Form() {{
          return (
            <main className="min-h-screen bg-surface-900 flex items-center justify-center p-4">
              <div className="w-full max-w-lg">
                <div className="bg-surface-800 rounded-xl p-6 md:p-8 shadow-xl">
                  <h1 className="text-2xl font-semibold text-text-primary mb-6">{page_name}</h1>
                  <form className="flex flex-col gap-4">
                    {{/* Form fields */}}
                    <div className="flex justify-end gap-3 mt-4">
                      <button type="button" className="px-4 py-2 rounded-lg text-text-secondary hover:bg-surface-700 transition-colors">
                        Cancel
                      </button>
                      <button type="submit" className="px-4 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white font-medium transition-colors">
                        Submit
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            </main>
          );
        }}
    """)


def _settings_layout(page_name: str, sections: list[str]) -> str:
    nav_items = [s for s in sections if s != "nav"]
    nav_jsx = "\n".join(
        f'              <a href="#{s}" className="px-3 py-2 rounded-lg text-text-secondary hover:bg-surface-700 transition-colors">{s.title()}</a>'
        for s in nav_items
    )
    panels_jsx = "\n\n".join(
        f'            <section id="{s}" className="bg-surface-800 rounded-xl p-6">\n'
        f'              <h2 className="text-lg font-semibold text-text-primary mb-4">{s.title()}</h2>\n'
        f'              {{/* {s.title()} settings */}}\n'
        f'            </section>'
        for s in nav_items
    )

    return textwrap.dedent(f"""\
        export default function {page_name}Page() {{
          return (
            <main className="min-h-screen bg-surface-900 p-4 md:p-6 lg:p-8">
              <div className="mx-auto max-w-4xl">
                <h1 className="text-2xl font-semibold text-text-primary mb-8">{page_name}</h1>
                <div className="flex flex-col md:flex-row gap-8">
                  <nav className="flex md:flex-col gap-1 md:w-48 shrink-0">
        {nav_jsx}
                  </nav>
                  <div className="flex-1 flex flex-col gap-6">
        {panels_jsx}
                  </div>
                </div>
              </div>
            </main>
          );
        }}
    """)


@tool
def scaffold_page_component(
    page_name: str,
    page_type: str = "content",
    description: str = "",
) -> str:
    """Scaffold a complete Next.js page component for App Router.

    Args:
        page_name: PascalCase name (e.g. 'TokenDetail', 'About', 'Onboarding').
        page_type: 'content' (static/dynamic content page), 'list' (collection
            with filters/search), 'detail' (single item view with back nav),
            or 'empty' (minimal skeleton).
        description: Brief description used as a code comment.
    """
    desc_comment = f"  // {description}\n" if description else ""

    if page_type == "list":
        return textwrap.dedent(f"""\
            import {{ Suspense }} from "react";

            {desc_comment}export default function {page_name}Page() {{
              return (
                <div className="flex flex-col gap-6">
                  <div className="flex items-center justify-between">
                    <h1 className="text-2xl font-semibold text-text-primary">{page_name}</h1>
                    <div className="flex gap-2">
                      {{/* Search input + filter buttons */}}
                    </div>
                  </div>
                  <Suspense fallback={{<div className="animate-pulse h-64 bg-surface-800 rounded-xl" />}}>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {{/* List item cards */}}
                    </div>
                  </Suspense>
                  <div className="flex justify-center">
                    {{/* Pagination */}}
                  </div>
                </div>
              );
            }}
        """)
    elif page_type == "detail":
        return textwrap.dedent(f"""\
            import Link from "next/link";
            import {{ Suspense }} from "react";

            {desc_comment}export default function {page_name}Page({{ params }}: {{ params: {{ id: string }} }}) {{
              return (
                <div className="flex flex-col gap-6">
                  <div className="flex items-center gap-3">
                    <Link href=".." className="text-text-secondary hover:text-text-primary transition-colors">
                      &larr; Back
                    </Link>
                    <h1 className="text-2xl font-semibold text-text-primary">{page_name}</h1>
                  </div>
                  <Suspense fallback={{<div className="animate-pulse h-96 bg-surface-800 rounded-xl" />}}>
                    <div className="bg-surface-800 rounded-xl p-6">
                      {{/* Detail content */}}
                    </div>
                  </Suspense>
                </div>
              );
            }}
        """)
    elif page_type == "empty":
        return textwrap.dedent(f"""\
            {desc_comment}export default function {page_name}Page() {{
              return <div>{{/* {page_name} */}}</div>;
            }}
        """)
    else:  # content
        return textwrap.dedent(f"""\
            import {{ Suspense }} from "react";

            {desc_comment}export default function {page_name}Page() {{
              return (
                <div className="flex flex-col gap-6">
                  <h1 className="text-2xl font-semibold text-text-primary">{page_name}</h1>
                  <Suspense fallback={{<div className="animate-pulse h-64 bg-surface-800 rounded-xl" />}}>
                    <div className="bg-surface-800 rounded-xl p-6">
                      {{/* Page content */}}
                    </div>
                  </Suspense>
                </div>
              );
            }}
        """)


FRONTEND_TOOLS = [
    scaffold_nextjs_component,
    generate_chart_component,
    generate_data_fetcher,
    scaffold_page_layout,
    scaffold_page_component,
]
