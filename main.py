import click
from app.i18n.strings import t
from app.config import APP_LANG


@click.group()
@click.option("--lang", default=APP_LANG, type=click.Choice(["en", "tr"]), help="Interface language")
@click.pass_context
def cli(ctx, lang):
    ctx.ensure_object(dict)
    ctx.obj["lang"] = lang


@cli.command()
@click.argument("url")
@click.pass_context
def summarize(ctx, url):
    lang = ctx.obj["lang"]
    click.echo(t("welcome", lang))
    click.echo(t("downloading", lang))
    click.echo(t("summarizing", lang))
    click.echo("TODO: implement")


@cli.command()
@click.argument("region")
@click.pass_context
def recommend(ctx, region):
    lang = ctx.obj["lang"]
    click.echo(t("welcome", lang))
    click.echo(t("fetching_reviews", lang, region))
    click.echo("TODO: implement")


@cli.command()
@click.argument("region")
@click.option("--budget", default=500, help="Budget in USD")
@click.option("--days", default=3, help="Number of days")
@click.option("--preferences", default="", help="Comma-separated preferences")
@click.pass_context
def plan(ctx, region, budget, days, preferences):
    lang = ctx.obj["lang"]
    click.echo(t("welcome", lang))
    click.echo(t("generating_plan", lang))
    click.echo("TODO: implement")


if __name__ == "__main__":
    cli()
