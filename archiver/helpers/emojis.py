loading = None
x = None
check = None


def get_emojis(bot):
    global loading
    global x
    global check

    loading = bot.get_emoji(478317750817914910)
    x = bot.get_emoji(475032169086058496)
    check = bot.get_emoji(475029940639891467)
