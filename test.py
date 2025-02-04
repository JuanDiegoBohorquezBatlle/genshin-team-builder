import genshin
import asyncio

async def interactive_login():
    try:
        # Initialize the genshin client
        client = genshin.Client()

        # Use the built-in interactive login method
        # This will prompt you to enter your username and password
        cookies = await client.login_with_password('suiyee16@gmail.com','Ilovemilo321!')

        # Retrieve cookies after logging in
        print("Cookies: ", cookies)

        return cookies

    except Exception as e:
        print(f"Error occurred: {e}")
        return None


asyncio.run(interactive_login())
