# StrikerX_Bot_Discord

Discord bot for one server. It answers slash commands, assigns a role when a member joins, creates a private category and text channel for each non-bot member, and opens a temporary voice room and text channel when someone joins the privacy voice channel. `/pdf-to-image` renders one page of an attached PDF as a PNG.

A Flask app listens on port 8000. `GET /` returns `Server is running!`.

## Setup

The bot reads `TOKEN` from the process environment. If that variable is unset, it loads `TOKEN` from a `.env` file in the project root. A variable already set in the environment is left as it is.

Windows Command Prompt:

```
set TOKEN=your-discord-bot-token
```

PowerShell:

```
$env:TOKEN = "your-discord-bot-token"
```

Copy `.env.example` to `.env` and set `TOKEN` there. Do not commit a real token.

## Run

```
python run.py
```

`python main.py` starts the same entry point. The hosting start command is not recorded in this repo. Confirm it with the original author before removing `main.py`.

## AI chat

When `OPENROUTER_API_KEY` is set, the bot answers `/ask` and messages that mention it. Those user messages are stored in a local SQLite file and sent to OpenRouter.

`/introduce` sets the name the bot uses for you in this server, and a missing name adds a short reminder on each AI reply there.

The file is `BOT_DB_PATH` (default `data/bot.db`). Turns are kept for `AI_HISTORY_DAYS` days (default 7). Token counts are not purged in this phase.

`/memory view` and `/memory clear` show or delete your stored turns. `/memory wipe-channel` deletes stored turns for that channel and requires Manage Messages.

`/persona show`, `/persona set`, and `/persona reset` read or change the server persona. Set and reset require Manage Server. Changing the persona clears that server's stored turns.

The other settings are `AI_MODEL`, `AI_REASONING_EFFORT`, `AI_MAX_TOKENS`, `AI_REQUESTS_PER_MINUTE`, `AI_DAILY_TOKEN_BUDGET`, `AI_HISTORY_DAYS`, `BOT_DB_PATH`, `OWNER_IDS`, and `DEV_GUILD_ID`. They load the same way `TOKEN` does.

`AI_REASONING_EFFORT` is `off`, `low`, `medium`, or `high`. The default is `low`.

`AI_MAX_TOKENS` defaults to 1024.

Reasoning tokens count toward that limit and toward the daily token budget, because the budget adds prompt and completion tokens as OpenRouter reports them.

A 400 response that included reasoning settings is retried once without reasoning settings.

If the reply text is empty and the finish reason is `length`, the bot says: "The answer was cut off before it finished. Please ask for a shorter answer."

When the key is empty, startup prints that AI chat will not load.

See `docs/ai-chat.md`.

## Commands

Slash commands are listed in `docs/commands.md`.

`/status` posts bot and host status in a public embed.

Set `DEV_GUILD_ID` to a server id to copy those commands to that server at startup.

An empty `DEV_GUILD_ID` syncs them globally.
