import asyncio
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneNumberInvalid, PhoneCodeExpired
import os
from dotenv import load_dotenv

load_dotenv() # Загружаем переменные окружения, чтобы получить API_ID и API_HASH

API_ID = int(os.getenv("PYROGRAM_API_ID"))
API_HASH = os.getenv("PYROGRAM_API_HASH")

async def generate_session_string():
    if not API_ID or not API_HASH:
        print("Please set PYROGRAM_API_ID and PYROGRAM_API_HASH in your .env file.")
        return

    print("Pyrogram Session String Generator")
    phone_number = input("Enter your phone number (e.g., +1234567890): ")

    # Use a dummy session name, as we'll get the string directly
    async with Client(":memory:", api_id=API_ID, api_hash=API_HASH) as app:
        try:
            sent_code = await app.send_code(phone_number)
            phone_code = input("Enter the verification code: ")
            
            try:
                await app.sign_in(phone_number, sent_code.phone_code_hash, phone_code)
            except PhoneCodeInvalid:
                print("Invalid verification code. Please try again.")
                return
            except PhoneCodeExpired:
                print("Verification code expired. Please restart the process.")
                return
            except SessionPasswordNeeded:
                two_fa_password = input("Enter your Two-Factor Authentication password: ")
                await app.check_password(two_fa_password)
            
            session_string = await app.export_session_string()
            print(f"\nYour Pyrogram session string:\n\n{session_string}\n")
            print(f"Please save this string. You will need to add it to your database via Admin Bot or directly to `user_accounts` table along with phone number: {phone_number}")

        except PhoneNumberInvalid:
            print("The phone number entered is invalid.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(generate_session_string())
