help me write README.md with the following context: this is a skeleton repository for a code quality evaluation and benchmarking project called 'code-bm'. It will contain set of prompts that will build a ficticious application called 'Raidio'. The following technology choices are mandatory: 
* The backend in 'backend/' uses  FastAPI - python 3.12 through uv;
* The frontend in 'frontend/' is ReactJS/Typescript application using bun; 
* The database in 'database/raidio.db' is strictly sqlite and the backend uses sqlalchemy to interact with it. 
* Any frontend or backend functionality is covered with unit, functional, and integration tests. Code quality and test coverage are recorded to 'code_quality.md'
* The Raidio application is managed via [taskfile](https://taskfile.dev/docs/guide)
* The application keeps live documentation in Markdown/wiki style in 'docs/' with main starting point of 'docs/index.md'
* There is a 'frontend/README.md' and 'backend/README.md' and they maintain precise notes on technical status of the frontend / backend application, how to use and extend them. 
* Usage of MCP and tools is encouraged, particularly for looking up latest documentation for each technology used.
