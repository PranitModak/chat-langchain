# Deployment

We recommend when deploying Chat LangChain, you use Vercel for the frontend, [LangGraph Cloud](https://langchain-ai.github.io/langgraph/cloud/) for the backend API, and GitHub action for the recurring ingestion tasks. This setup provides a simple and effective way to deploy and manage your application.

## Prerequisites

First, fork [chat-langchain](https://github.com/langchain-ai/chat-langchain) to your GitHub account.

## ChromaDB (Vector Store)

This project uses ChromaDB as the vector store, which runs locally and doesn't require any external setup. The vector database is stored in the `chroma_db/` directory and is automatically created when you run the ingestion process.

For local development, no additional setup is required. The ChromaDB instance will be created automatically when you run:

```bash
python backend/ingest.py --mode web --wipe
```

For production deployment, you may want to consider using a persistent storage solution or a managed ChromaDB service if you need to scale beyond local storage.

## Supabase (Record Manager)

Visit Supabase to create an account [here](https://supabase.com/dashboard).

Once you've created an account, click "New project" on the dashboard page.
Follow the steps, saving the database password after creating it, we'll need this later.

Once your project is setup (this also takes a few minutes), navigate to the "Settings" tab, then select "Database" under "Configuration".

Here, you should see a "Connection string" section. Copy this string, and insert your database password you saved earlier. This is your `RECORD_MANAGER_DB_URL` environment variable.

That's all you need to do for the record manager. The LangChain RecordManager API will handle creating tables for you.

## Vercel (Frontend)

First, build the frontend and confirm it's working locally:

```shell
cd frontend
yarn
yarn build
```

Then, create a Vercel account for hosting [here](https://vercel.com/signup).

Once you've created your Vercel account, navigate to [your dashboard](https://vercel.com/) and click the button "Add New..." in the top right.
This will open a dropdown. From there select "Project".

On the next screen, search for "chat-langchain" (if you did not modify the repo name when forking). Once shown, click "Import".

Finally, click "Deploy" and your frontend will be deployed!

## GitHub Action (Recurring Ingestion)

Now, in order for your vector store to be updated with new data, you'll need to setup a recurring ingestion task (this will also populate the vector store for the first time).

Go to your forked repository, and navigate to the "Settings" tab.

Select "Environments" from the left-hand menu, and click "New environment". Enter the name "Indexing" and click "Configure environment".

When configuring, click "Add secret" and add the following secrets:

```
GOOGLE_API_KEY=
RECORD_MANAGER_DB_URL=
```

These should be the same secrets as were added to Vercel.

Next, navigate to the "Actions" tab and confirm you understand your workflows, and enable them.

Then, click on the "Update index" workflow, and click "Enable workflow". Finally, click on the "Run workflow" dropdown and click "Run workflow".

Once this has finished you can visit your production URL from Vercel, and start using the app!

## Run and deploy backend API server

If you have a valid LangGraph Cloud [license key](https://langchain-ai.github.io/langgraph/cloud/deployment/self_hosted/), you can run a fully functional LangGraph server locally with a `langgraph up` command. Otherwise, you can use `langgraph test` to test that the API server is functional.

> [!NOTE]
> When running `langgraph test`, you will only be able to [create stateless runs](https://langchain-ai.github.io/langgraph/cloud/how-tos/cloud_examples/stateless_runs/), and the previous chats functionality will not be available.

Once you confirm that the server is working locally, you can deploy your app with [LangGraph Cloud](https://langchain-ai.github.io/langgraph/cloud/).

## Connect to the backend API (LangGraph Cloud)

In Vercel add the following environment variables:
- `API_BASE_URL` that matches your LangGraph Cloud deployment API URL
- `NEXT_PUBLIC_API_URL` - API URL that LangGraph Cloud deployment is proxied to, e.g. "https://chat.langchain.com/api"
- `LANGCHAIN_API_KEY` - LangSmith API key