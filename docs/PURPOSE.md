Purpose

ForgeOps is the operational work ledger for the AI development ecosystem.

Its purpose is to track issues, tasks, assignments, and progress across 
multiple repositories so that AI-assisted development remains organized, 
reviewable, and resumable across time.

ForgeOps maintains the authoritative record of what work exists, what 
state that work is in, who or what is responsible for executing it, and 
what outcomes were produced. By preserving this operational history, 
ForgeOps allows developers and AI agents to coordinate work across 
repositories while maintaining continuity between development sessions.

ForgeOps enables a parallel workflow where AI agents can continue 
executing tasks while human developers review completed work. It keeps 
the development process legible even as AI systems increase the speed 
and volume of generated code.

ForgeOps is not responsible for executing code tasks, managing secrets, 
or handling infrastructure connections. Those responsibilities belong 
to other components in the system architecture.

Specifically:

- Task execution is handled by JCT.
- Secrets management is handled by Aegis.
- Infrastructure connections are handled by Charon.
- Atomic executable actions are defined by the action-registry.

ForgeOps focuses exclusively on tracking work and progress across 
repositories so that the overall development process remains visible, 
coherent, and controllable.
