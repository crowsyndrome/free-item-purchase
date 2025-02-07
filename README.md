# Roblox Free Item Purchase

An automated Python script that helps you collect all available free items from the Roblox catalog. The script automatically finds and purchases free collectible items using your Roblox account.

## Features

- Automatically finds all free items in the Roblox catalog
- Caches item data to prevent unnecessary API calls
- Handles rate limiting gracefully
- Provides colored console output for better visibility

## Prerequisites

- Python 3.7 or higher
- A Roblox account
- Your Roblox `.ROBLOSECURITY` cookie

## Installation

1. Clone the repository:
```bash
git clone https://github.com/netpwned/free-item-purchase.git
cd free-item-purchase
```

2. Install the required dependencies:
```bash
pip install curl-cffi colorama
```

3. Create a `cookie.txt` file in the project directory and paste your Roblox `.ROBLOSECURITY` cookie into it:

## Getting Your Roblox Cookie

1. Log into your Roblox account in a web browser
2. Press F12 to open Developer Tools
3. Go to the "Application" or "Storage" tab
4. Look for "Cookies" in the sidebar
5. Find the `.ROBLOSECURITY` cookie
6. Copy the value (without any quotes) into your `cookie.txt` file

## Usage

Run the script:
```bash
py main.py
```

The script will:
1. Authenticate using your cookie
2. Fetch all available free items (if not cached)
3. Attempt to purchase each item
4. Display the progress with colored output

## File Structure

- `main.py` - The main script
- `cookie.txt` - Your Roblox security cookie (you need to create this)
- `free_items_cache.json` - Cache of found free items (automatically created)

## Error Handling

- If the script encounters rate limiting, it will wait for 60 seconds before retrying
- Failed purchases will be logged but won't stop the script
- Invalid cookies will result in an authentication error

## Troubleshooting

### Common Issues:

1. **Authentication Failed**
   - Verify your cookie is correct and not expired
   - Make sure cookie.txt contains only the cookie value, no quotes or extra spaces

2. **Rate Limiting**
   - This is normal, the script will automatically wait and retry
   - If it happens too frequently, try running the script at a different time

## Contributing

Feel free to fork the repository and submit pull requests for any improvements you make.
