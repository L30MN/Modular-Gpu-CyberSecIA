# Agent prompts

System prompts for the custom agents defined in Open WebUI. Each agent is a
configuration (system prompt + attached knowledge collections + tools) that runs
on top of the chat model — see `ARCHITECTURE.md`.

## Language note

**These prompts are written in Italian on purpose.** They are not documentation:
they are the actual system prompts fed to the model, and they instruct the agent
to tutor the user **in Italian**. Translating a prompt would change the language
the agent answers in. If you want the agent in another language, translate the
prompt and adjust the "respond in Italian" instruction accordingly.

## Prompts

| File | Agent | Purpose |
|---|---|---|
| `pentest-mentor.md` | Pentest Mentor | An offensive-security tutor for authorized labs (CTF, HackTheBox/TryHackMe, own VMs). Uses the knowledge base (OWASP, MITRE ATT&CK, CWE, CAPEC), cites sources, and teaches one step at a time. |

## Usage

In Open WebUI: **Workspace → Models →** create/edit a model, paste the prompt
into the **System Prompt** field, attach the relevant knowledge collections, and
(optionally) enable the agent's tools at the model level so they persist.
