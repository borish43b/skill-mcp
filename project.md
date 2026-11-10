# Task
Create a small, lightweight mcp server in python that serves skills to a LLM that is capable to use tools. The server shall have the following parameters:
`--host <IP>` The host address. Default 127.0.0.1
`--port <PORT>` The port on which the service runs
`--skills-dir <DIR>` a folder that contains skills in organized in sub folders as following: `skill_name/SKILL.md` where `skill_name` is a sub folder of the specified `DIR`


The server shall allow to query for available skills and to get the actual skill.

Lightweight means: As little dependencies as possible and easy to run. Suggest libraries before you start.

The whole project shall be contained in /workspace/skill_mcp/


