[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/getsimpletool-mcpo-simple-server-badge.png)](https://mseep.ai/app/getsimpletool-mcpo-simple-server)

# MCPoSimpleServer

A Python-based LLM server that implements the Model Context Protocol (MCP).

## 🤔 What is MCPoSimpleServer?

MCPoSimpleServer is a lightweight, asynchronous API platform for running and managing MCP tools in isolated, secure environments. It implements the Model Context Protocol (MCP) for seamless integration with LLM applications.

## 📺 Demo

Check out our demo video to see MCPoSimpleServer in action:

[![MCPoSimpleServer Demo](https://img.youtube.com/vi/tQ6OhvC4eDQ/0.jpg)](https://www.youtube.com/watch?v=tQ6OhvC4eDQ)

## ✨ Key Features

- ✨ Local Docker container – your own local Docker container with a single SSE-MCP connection
- ⚡ Support quick and easy load any MCP tool launched via `uvx` or `npx`
- 🔄 Dynamic tool loading and filtering (whitelist/blacklist)
- 🌐 Access to MCP tools via SSE, Swagger REST, and OpenAPI.json (compatible with OpenWebUI)
- 🐳 Tool isolation – each tool runs in its own thread
- 🗄️ JSON-based configuration – easy to edit and portable
- 🧑‍💻 Ability to launch your own MCP server with custom ENV parameters
- 🛡️ Bearer admin hack – simple admin authorization (ideal for testing and quick changes)
- 📝 Async FastAPI Python server with full type hints for code clarity and safety
- ✅ PyTest – fast and easy verification of changes on a running server

## 🎉 What we have now

- 🔗 Docker container built on Debian 13 with FastAPI/Python 3.13 server
- ⚡ Support quick and easy load any MCP tool launched via `uvx` or `npx`
- 🌐 Access to MCP tools via SSE, Swagger REST, and OpenAPI.json (OpenWebUI compatible)
- 🆒 SupervisorD controlled by ENV allows running SSHD + Xfce + noVNC (desktop via web/port 6901, ~260MB)
- 🔄 Dynamic tool loading and filtering from MCP server (whitelist/blacklist)
- 🧵 Each MCP server runs in its own thread
- 🗄️ No need for a database – JSON configuration for easy editing and portability
- 🧑‍💻 Users can define their own MCP server with custom ENV (auto-detected via Auth Bearer)
- 🛡️ Env Bearer Admin Hack – configurable env simulating Bearer admin (ideal for tests and quick changes)
- 📝 Built entirely on FastAPI Python + Pydantic for code clarity and safety
- ❌ Custom SSE stack based only on FastAPI (no Starlette)
- ✅ PyTest – tests run a live server instance and perform tests on a real running server (no mocking!)

## 🚀 Working on

- 🤔 Prompts – fixing some bugs with class injection into SSE
- 🖥️ WebUI Frontend with Marketplace (click and install)
