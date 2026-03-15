from fastmcp.prompts import Message

from mcp_assistant.config import (
    COPILOT_INSTRUCTIONS,
    INDEX_FILE,
    PLANS_DIR,
    PRDS_DIR,
    SPEC_ASSISTANT_DIR,
    SPECS_DIR,
)


def register(mcp) -> None:
    @mcp.prompt()
    def prd_from_idea(idea: str) -> list[Message]:
        """Gera prompt para criar PRD a partir de uma ideia, injetando protocolo e estado do index."""
        protocol = COPILOT_INSTRUCTIONS.read_text() if COPILOT_INSTRUCTIONS.exists() else ""
        index_content = INDEX_FILE.read_text() if INDEX_FILE.exists() else "index.md ainda não existe."
        prd_prompt_template = (SPEC_ASSISTANT_DIR / "prd-prompt.md").read_text() if (SPEC_ASSISTANT_DIR / "prd-prompt.md").exists() else ""

        system_content = f"{prd_prompt_template}\n\n---\n\n# PROTOCOLO DE GOVERNANÇA\n{protocol}"
        user_content = (
            f"# Estado Atual do Index\n\n{index_content}\n\n"
            f"---\n\n# Nova Ideia\n\n{idea}\n\n"
            "Por favor, gere o PRD correspondente seguindo o protocolo acima."
        )

        return [
            Message(role="user", content=system_content + "\n\n" + user_content),
        ]

    @mcp.prompt()
    def spec_from_prd(prd_filename: str) -> list[Message]:
        """Gera prompt para criar Spec a partir de um PRD."""
        prd_path = PRDS_DIR / prd_filename
        if not prd_path.exists():
            raise ValueError(f"PRD '{prd_filename}' não encontrado.")

        prd_content = prd_path.read_text()
        tech_spec_template = (SPEC_ASSISTANT_DIR / "tech-spec-prompt.md").read_text() if (SPEC_ASSISTANT_DIR / "tech-spec-prompt.md").exists() else ""

        user_content = (
            f"{tech_spec_template}\n\n"
            f"---\n\n# PRD: {prd_filename}\n\n{prd_content}\n\n"
            "Por favor, decomponha este PRD em Especificações Técnicas (Specs) seguindo o protocolo acima."
        )

        return [
            Message(role="user", content=user_content),
        ]

    @mcp.prompt()
    def plan_from_spec(spec_filename: str) -> list[Message]:
        """Gera prompt para criar Plan a partir de uma Spec."""
        spec_path = SPECS_DIR / spec_filename
        if not spec_path.exists():
            raise ValueError(f"Spec '{spec_filename}' não encontrada.")

        spec_content = spec_path.read_text()

        example_plan = ""
        example_plans = sorted(PLANS_DIR.glob("*.md")) if PLANS_DIR.exists() else []
        if example_plans:
            example_plan = example_plans[0].read_text()

        user_content = (
            f"# Spec de Referência: {spec_filename}\n\n{spec_content}\n\n"
            f"---\n\n# Exemplo de Estilo de Plan\n\n{example_plan}\n\n"
            "---\n\n"
            "Por favor, gere um Plan no mesmo estilo do exemplo acima, com base na Spec fornecida. "
            "O arquivo deve ser salvo em `plans/` com o padrão `plan-<nome-da-feature>.prompt.md`."
        )

        return [
            Message(role="user", content=user_content),
        ]

    @mcp.prompt()
    def review_artefact(filename: str, artefact_type: str) -> list[Message]:
        """
        Gera prompt de revisão de compliance para um artefato.
        artefact_type: 'prd' | 'spec' | 'plan'
        """
        dirs = {"prd": PRDS_DIR, "spec": SPECS_DIR, "plan": PLANS_DIR}
        if artefact_type not in dirs:
            raise ValueError(f"artefact_type inválido: '{artefact_type}'")

        path = dirs[artefact_type] / filename
        if not path.exists():
            raise ValueError(f"Arquivo '{filename}' não encontrado em {dirs[artefact_type]}.")

        content = path.read_text()
        protocol = COPILOT_INSTRUCTIONS.read_text() if COPILOT_INSTRUCTIONS.exists() else ""

        user_content = (
            f"# Protocolo de Governança\n\n{protocol}\n\n"
            f"---\n\n# Artefato para Revisão ({artefact_type.upper()}): {filename}\n\n{content}\n\n"
            "---\n\n"
            "Por favor, revise este artefato verificando aderência ao protocolo acima. "
            "Indique explicitamente cada item do checklist de compliance e aponte problemas se houver."
        )

        return [
            Message(role="user", content=user_content),
        ]
