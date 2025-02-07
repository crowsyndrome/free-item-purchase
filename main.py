import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional

from colorama import init, Fore, Style
from curl_cffi import requests

init()

COOKIE_FILE = "cookie.txt"
CACHE_FILE = "free_items_cache.json"
RATE_LIMIT_WAIT = 60  # seconds


class PurchaseStatus(Enum):
    SUCCESS = "SUCCESS"
    RATE_LIMITED = "RATE_LIMITED"
    FAILED = "FAILED"


@dataclass
class ItemDetails:
    asset_id: str
    collectible_item_id: str
    collectible_product_id: str


class Logger:
    @staticmethod
    def success(message: str) -> None:
        print(f"{Fore.GREEN}[✓] {message}{Style.RESET_ALL}")

    @staticmethod
    def error(message: str) -> None:
        print(f"{Fore.RED}[✗] {message}{Style.RESET_ALL}")

    @staticmethod
    def info(message: str) -> None:
        print(f"{Fore.BLUE}[i] {message}{Style.RESET_ALL}")

    @staticmethod
    def warning(message: str) -> None:
        print(f"{Fore.YELLOW}[!] {message}{Style.RESET_ALL}")


class RobloxSession:
    def __init__(self):
        self.session = requests.Session(
            impersonate="safari_ios",
            headers={
                "cookie": f".ROBLOSECURITY={self._load_cookie()}",
                "authority": "www.roblox.com",
            }
        )
        self.assign_csrf_token()
        self.user_id = self.get_authenticated_user_id()  # Fetch authenticated user id once
        Logger.info(f"Authenticated as user id: {self.user_id}")

    def _load_cookie(self) -> str:
        try:
            if not os.path.exists(COOKIE_FILE):
                raise FileNotFoundError(
                    "Cookie file not found. Please create cookie.txt with your .ROBLOSECURITY cookie.")

            with open(COOKIE_FILE, "r") as f:
                cookie = f.read().strip()
                if not cookie:
                    raise ValueError("Cookie file is empty. Please add your .ROBLOSECURITY cookie.")
                return cookie
        except Exception as e:
            Logger.error(f"Cookie loading failed: {str(e)}")
            raise

    def assign_csrf_token(self) -> None:
        try:
            response = self.session.get("https://www.roblox.com/home")
            token = response.text.split('"csrf-token" data-token="')[1].split('"')[0]
            self.session.headers["x-csrf-token"] = token
            Logger.success("CSRF token assigned successfully")
        except Exception as e:
            Logger.error(f"Failed to retrieve CSRF token: {str(e)}")
            raise

    def get_authenticated_user_id(self) -> int:
        try:
            response = self.session.get("https://users.roblox.com/v1/users/authenticated")
            response.raise_for_status()
            data = response.json()
            user_id = data.get("id")
            if not user_id:
                raise ValueError("Authenticated user id not found in response")
            return user_id
        except Exception as e:
            Logger.error(f"Failed to get authenticated user id: {str(e)}")
            raise


class ItemFetcher:
    def __init__(self, session: RobloxSession):
        self.session = session

    def fetch_item_details(self, asset_id: str) -> Optional[Dict[str, Any]]:
        details_url = f"https://economy.roblox.com/v2/assets/{asset_id}/details"
        try:
            response = self.session.session.get(details_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            Logger.error(f"Failed to fetch details for asset {asset_id}: {str(e)}")
            return None

    def fetch_items(self) -> Dict[str, ItemDetails]:
        result: Dict[str, ItemDetails] = {}
        cursor = ""

        while cursor is not None:
            url = (
                "https://catalog.roblox.com/v1/search/items/details?"
                "Category=1&CreatorType=1&CreatorName=Roblox&Limit=30&"
                f"MaxPrice=0&MinPrice=0&SortAggregation=5&SortType=3&cursor={cursor}"
            )

            try:
                req = self.session.session.get(url)
                if req.status_code == 429:
                    Logger.warning(f"Rate limited while fetching items. Waiting {RATE_LIMIT_WAIT} seconds...")
                    time.sleep(RATE_LIMIT_WAIT)
                    continue

                res = req.json()
                for item in res.get("data", []):
                    self._process_item(item, result)

                cursor = res.get("nextPageCursor")

            except Exception as e:
                Logger.error(f"Error fetching items: {str(e)}")
                break

        return result

    def _process_item(self, item: Dict[str, Any], result: Dict[str, ItemDetails]) -> None:
        item_name = item.get("name")
        asset_id = str(item.get("id"))
        collectible_item_id = item.get("collectibleItemId")

        if not collectible_item_id:
            return

        details = self.fetch_item_details(asset_id)
        if not details:
            return

        collectible_product_id = details.get("CollectibleProductId")
        if not collectible_product_id:
            Logger.warning(f"No collectibleProductId found for {item_name} (asset id {asset_id}). Skipping.")
            return

        result[item_name] = ItemDetails(
            asset_id=asset_id,
            collectible_item_id=collectible_item_id,
            collectible_product_id=collectible_product_id
        )
        Logger.info(f"Cached item: {item_name}")


class ItemPurchaser:
    def __init__(self, session: RobloxSession):
        self.session = session

    def purchase(self, item_name: str, item_details: ItemDetails) -> PurchaseStatus:
        url = f"https://apis.roblox.com/marketplace-sales/v1/item/{item_details.collectible_item_id}/purchase-item"
        payload = {
            "collectibleItemId": item_details.collectible_item_id,
            "collectibleProductId": item_details.collectible_product_id,
            "expectedCurrency": 1,
            "expectedPrice": 0,
            "expectedPurchaserId": str(self.session.user_id),
            "expectedPurchaserType": "User",
            "expectedSellerId": 1,
            "expectedSellerType": "User",
            "idempotencyKey": str(uuid.uuid4())
        }

        while True:
            try:
                req = self.session.session.post(url, json=payload)
                response_json = req.json()

                if response_json.get("errors") == [{"message": "", "code": 0}]:
                    Logger.warning(f"Rate limited while purchasing {item_name}. Waiting {RATE_LIMIT_WAIT} seconds...")
                    time.sleep(RATE_LIMIT_WAIT)
                    continue

                success = "purchased" in req.text.lower() or "success" in req.text.lower()
                if success:
                    Logger.success(f"Successfully purchased {item_name}")
                    return PurchaseStatus.SUCCESS
                else:
                    Logger.error(f"Failed to purchase {item_name}: {req.text}")
                    return PurchaseStatus.FAILED

            except Exception as e:
                Logger.error(f"Error purchasing {item_name}: {str(e)}")
                return PurchaseStatus.FAILED


class CacheManager:
    @staticmethod
    def save_items(items: Dict[str, ItemDetails]) -> None:
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump({name: vars(details) for name, details in items.items()}, f, indent=2)
            Logger.success(f"Items cached successfully to {CACHE_FILE}")
        except Exception as e:
            Logger.error(f"Failed to cache items: {str(e)}")

    @staticmethod
    def load_items() -> Dict[str, ItemDetails]:
        try:
            if not os.path.exists(CACHE_FILE):
                return {}

            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                return {name: ItemDetails(**details) for name, details in data.items()}
        except Exception as e:
            Logger.error(f"Failed to load cached items: {str(e)}")
            return {}


def main():
    Logger.info(f"Starting item buyer at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        session = RobloxSession()
        fetcher = ItemFetcher(session)
        purchaser = ItemPurchaser(session)

        items = CacheManager.load_items()
        if not items:
            Logger.info("Cache is empty, fetching items...")
            items = fetcher.fetch_items()
            CacheManager.save_items(items)

        Logger.info(f"Found {len(items)} items to process")
        for item_name, details in items.items():
            purchaser.purchase(item_name, details)

        Logger.success("Processing completed successfully")

    except Exception as e:
        Logger.error(f"Program terminated due to error: {str(e)}")
        raise


if __name__ == "__main__":
    main()
