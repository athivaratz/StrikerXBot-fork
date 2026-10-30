# Commands

The bot registers slash commands when it starts.

Set `DEV_GUILD_ID` to a server id to copy those commands to that server. They show up immediately during development.

With `DEV_GUILD_ID` empty, startup syncs the commands globally.

Discord can take time to show a new global command.

The bot needs permission to send messages in the channel.

Extra permissions are named on the command that needs them.

An ephemeral reply is visible only to the person who ran the command.

`/ask`, `/memory`, and `/persona` are registered only when `OPENROUTER_API_KEY` is set.

## /help

`/help` lists the slash commands that are registered, with group subcommands written as `/group sub`.

The list comes from the command tree, so it matches whatever loaded at startup.

The reply is ephemeral.

```
/help
```

## /clear

`/clear` deletes recent messages in this channel.

`amount` is how many messages to delete. It must be from 1 to 100. The default is 100.

The user needs Manage Messages.

Discord shows the command to members with that permission.

The bot needs Manage Messages and Read Message History in the channel.

The reply is ephemeral.

```
/clear amount: 20
```

## /role

`/role` adds, removes, or replaces a member's role. It runs in a server.

The user needs Manage Roles.

Discord shows the command to members with that permission.

The bot needs Manage Roles.

Its highest role must sit above the role it changes.

Each subcommand takes a member and a role.

```
/role add
/role remove
/role replace
```

`/role add` gives that role.

`/role remove` takes that role away.

`/role replace` removes the member's other roles, then adds the chosen role.

The command refuses `@everyone` and managed roles.

It refuses a role at or above your highest role, unless you are the server owner.

It refuses a role at or above the bot's highest role.

It refuses a member whose highest role is at or above yours, unless you are the server owner.

Only the server owner can change the server owner's roles.

`/role replace` skips managed roles.

It also skips roles at or above the bot's highest role, and roles at or above your highest role unless you are the owner.

The reply names each skipped role.

Every `/role` reply is ephemeral.

The text uses the member's name and the role's name.

## /pdf-to-image

`/pdf-to-image` renders one page of an attached PDF as a PNG.

The image is posted in the channel.

Errors are ephemeral.

`page` starts at 1.

`dpi` runs from 72 to 300. The default is 150.

The file name must end with `.pdf`.

The check is case-insensitive.

The file must be 10 MB or smaller. The size is checked before the file is read.

The page must exist in the file.

A password-protected PDF is rejected.

A corrupt PDF is rejected.

The PDF is opened from memory.

The bot needs Attach Files in the channel to send the PNG.

```
/pdf-to-image file page dpi
```

## /ask

`/ask` sends the prompt through the AI chat path. The reply is public.

```
/ask prompt: What is on the schedule?
```

See `docs/ai-chat.md` for history, limits, and the model.

## /memory

`/memory` shows or deletes stored AI turns. Replies are ephemeral.

`/memory view` reports how many of your turns are stored in this channel, plus your last 3 messages there.

`/memory clear` deletes your turns. `scope` is `channel` or `everywhere`. `channel` is the default.

`/memory wipe-channel` deletes every stored turn in this channel.

It runs in a server.

The user needs Manage Messages.

```
/memory view
/memory clear scope: everywhere
/memory wipe-channel
```

## /persona

`/persona` shows or changes this server's AI persona.

It runs in a server.

Replies are ephemeral.

`/persona show` prints the persona and says whether it is the default or a custom one.

`/persona set` stores a custom persona. The user needs Manage Server.

Empty text is rejected.

Text longer than 1500 characters is rejected.

`/persona reset` removes the saved persona. The user needs Manage Server.

Later replies use the default persona.

```
/persona show
/persona set text: You are a helpful bot.
/persona reset
```

## Changes from the prefix commands

`-hello`, `-bye`, and `-today` are removed.

`/help` is built from the commands registered at startup.

`-help` sent one fixed sentence.

`/clear` takes an amount from 1 to 100 and replies privately.

`-clear` deleted 100 messages and posted the count in the channel.

`/role` requires Manage Roles.

`-role` required Manage Messages.

This is an intentional security change because the old command let anyone with Manage Messages give any role, including admin roles, to anyone.

`/role` checks the role hierarchy before it changes anyone.

`/role replace` skips managed roles and roles at or above the bot's highest role. It also skips roles at or above your highest role unless you are the owner. The reply names the skipped roles.

`-role` removed every role except `@everyone`, then added the new role.

`/pdf-to-image` rejects a file over 10 MB.

`dpi` defaults to 150.

`-pdf-to-image` always rendered at 300 DPI and wrote a temp file on disk.
