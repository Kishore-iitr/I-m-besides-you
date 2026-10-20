# AI Usage Log

## Disclosure of Generative AI Assistance

In accordance with the task instructions ("You are free to use generative AI. Please record how you used it in your work log."), this document logs all generative AI usage across design, coding, prompt development, and analysis.

### System Architecture & Modeling
- **Reference**: Jiang et al., "Inducing Task Models from Computer-Use Traces", arXiv 2608.20319.
- **Role assignments**:
  - `GROUNDING_MODEL`: Action description and screen extraction for raw events / bursts.
  - `REASONING_MODEL`: Activity segmentation and task-thread hierarchical clustering.
  - `MOCK_ENGINE`: Deterministic heuristic baseline that operates with 0 API calls for testing, structure verification, and offline execution.

### Usage Record
- Model: Built-in deterministic mock + LLM provider adapter (Puter / OpenRouter / Anthropic / OpenAI / Gemini).
- Temperature: 0.2 default (strict reproducibility).
- Validation: Zod schemas for all JSON outputs with automatic retry / repair pass.
