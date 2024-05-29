# About

A stand alone Hell Let Loose server status tool for servers running [Community RCON](https://github.com/MarechJ/hll_rcon_tool) with some excellent features!

- It's fast! runs asynchronously (with `trio`) so that it can update a bunch of different webhooks at the same time
- Respects `Discord` rate limiting and if it is being rate limited will sleep the amount of time `Discord` asks.
- Separate and independent sections (server info header, game state [time remaining, etc.] and map rotations)
- User configurable refresh rates per section
- User configurable text for most portions so you can tweak, translate or otherwise localize it for your users.
- Host as many servers as you want and/or have one server update multiple web hooks
- Now with more fault tolerance! It won't kill the entire process if an individual config file has issues

![Server Header](docs/images/example_header.png)
![Game State](docs/images/example_gamestate.png)
![Map Rotation](docs/images/example_map_rotation.png)

# Requirements

- Either `Docker` or Python `3.11`+

You can _probably_ in theory run this anywhere that supports `Docker` or if running it stand alone Python `3.10`+, but I only tested it on `Linux` and with Python `3.11`, anything else is up to you.

- Disk space / RAM

You don't need much, enough to run your distro and Docker, mine is running on an `alpine` Linux container using ~2gb of disk space and less than 200mb of RAM.

# Installing

1. Clone the repository **or** download a release:
2. Substitute <release version> with the desired release, such as `v1.4.0`

```sh
git clone https://github.com/cemathey/hll_server_status.git
cd hll_server_status
git checkout <release version>
```

## Using Docker (recommended)

1. Pull the `Docker` `image`:

```sh
docker compose pull
```

2. Configure as many servers as you want, copy `default_config.toml` into the `config/` directory and fill it out (See the configuration section)

3. Run it!

```sh
docker compose up -d
```

## Using Python (Standalone, no Docker)

1. I'd recommend just running this with `Docker`, otherwise you'll have to make sure you have a compatible version of `Python` and [poetry](https://python-poetry.org/) and you'll just have to figure all that out on your own.

2. If you do choose to go this route, make sure you create a virtual environment so you don't pollute your global packages.

3. You may find [hapless](https://github.com/bmwant/hapless) useful to let it run in the background.

# Configuring

- You can host as many different servers, or the same server updating different webhooks in the same tool as you want, simply copy the default config (do not delete or otherwise edit the default) use your editor of choice to fill it in. It is a [TOML](https://toml.io/en/) file and most values are set to usable defaults.

- There should be no real practical limit to the number of webhooks you can update with this, but who knows you might run into some weird `Discord` rate limiting on their end at some point and even though it uses `async` it's still subject to the [Python Global Interpreter Lock](https://realpython.com/python-gil/) and is only running on one thread on one core.

```sh
cp default_config.yml config/desired_name.yml
```

## Mandatory Configuration

Set your webhook

```yaml
discord:
  # In the format https://discord.com/api/webhooks/.../...
  webhook_url: ""
```

Set your server URL and API key

```yaml
api:
  # The URL or IP address of your CRCON, trailing / optional
  # for instance http://<ip>:<port>/ or https://yoururl.whatever/
  base_server_url: ""
  # CRCON API keys are generated from the admin site
  api_key: ""
  ```

# Updating

1. Refresh the `git` repository **or** download a new release, but see the release notes for any `default_config.yml` changes.
2. Substitute <release version> with the desired release, such as `v1.4.0`

```sh
git pull
git checkout <release version>
docker compose pull
docker compose up -d
```

# FAQ

1. Any plans to support Battlemetrics RCON?

   No.

2. Something is broken (look at [the Troubleshooting section](#troubleshooting))

   Open a GitHub issue please and include the complete stack trace of your error message if something is truly broken.

3. Any plans to include player statistics/score?

   ~~No, Scorebot which is built into Community RCON already includes this.~~
   Just kidding, I added it.

5. Any plans to include vote map info?
   Maybe at some point.

6. I can't get this working, will you help me?

   Not beyond this README, it's open source and if you can't figure out how to get it running contact me and I will [host it for you](https://crcon.cc/) for a nominal fee.

8. I don't know how to use Docker, help!

   Start Googling.

# Troubleshooting

- How do I change the logging level?

  Change `LOGURU_LEVEL` in your compose file to a different log level (`DEUBG`, `INFO`, `ERROR`, etc) and re-up your container

```shell
docker compose up -d
```
- My different sections appear in a different order than I want them to

Just delete one message at a time that you consider out of order, the tool will recreate them if it can't find them to edit it. Because these messages are created asynchronously it's more trouble than it's worth to try to force them to update or be created in a specific order.

# Miscellaneous

If you like what I do and would like me to continue volunteering my time, consider [tossing me a few dollars](https://www.buymeacoffee.com/emathey1).

# Contributing

Pull requests are welcome, please format your code with `black` and `isort` and include a descriptive pull request of what you would like to change and why.

# Planned Features

I may get to these at some point, if you **really** want something done you can either fork this or open a pull request, or you can commision me to make changes.

- Vote map information
