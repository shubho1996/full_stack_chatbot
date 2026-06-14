Full Stack Production Ready Chat Bot

Features:
1. Agentic Chat Bot.
2. It will have based on ReAct Framework.
3. Langchain + Langgraph + Arize Phoneix(Trace and Evals)
4. It will have new chat + resume chat
5. It will have memory. Both Short Term and Long Term
6. It will use postgres for saving chats data as threads.
7. It will also use the same dataset for storing memory.
8. It will be on React front-end.
9. It will have multiple user registration and session capabilities.
10. Will dockerise both the front end and backend to run multiple instances as same time.
11. Will add python load-balancer to router the queries to a specific instance.
12. It will have initially access to following tools:
    - File System tools
    - Google Search
    - Document Ingestion
13. Once any document is ingested. It will be added to a vector store under a specific user-id.
14. Also it will do rag based query as one of the tools.
15. It will also have Arize do all production-grade tracing and evaluations.
16. It will check and log the following metrices:
    - Answer accuracy
    - Hallucinations check for relevant query.
    - Groundness
17. It will also add Guardrails after the user query and before showing answer so that no harmful prompt injection or harmful response is show.
18. It will also have a small planner agent that will decide on the fly based on the query complexity how many retires are allowed.
19. When calling a tool it will the previous tool call and if its the same or not. and it can only retry same tool call with same parameter 2 times after that it should move to the next step and provide answer with what it already has.
20. For everything as of now, we need to use `gpt-5.4-nano`. 
21. the load-balancer I mentioned earlier, it should increase and decrease the number of instance based on the user queue -> min 1 max 4.
22. Also use open_ai llm for llms calls and for embedding use mini_lm_l6_v2 from sentence_Transformer to create vectors for a pdf.