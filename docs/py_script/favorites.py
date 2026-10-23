import json

from js import document, window
from pyodide.ffi import create_proxy


WISHLIST_STORAGE_KEY = "unisole-wishlist"
PAGE_DIRECTORY = str(window.location.pathname).rsplit("/", 1)[0]
RESOURCE_PREFIX = "../" if PAGE_DIRECTORY.endswith("/html") else ""
STORE_ASSET_DIRECTORY = f"{RESOURCE_PREFIX}store_assets/"
favorite_toast_timer = None
favorite_callbacks = []


def load_wishlist():
    stored_value = window.localStorage.getItem(WISHLIST_STORAGE_KEY)
    if stored_value is None:
        return {}

    wishlist = json.loads(str(stored_value))
    if not isinstance(wishlist, dict):
        raise ValueError("Stored wishlist data must be a JSON object.")
    return wishlist


def save_wishlist(wishlist):
    window.localStorage.setItem(WISHLIST_STORAGE_KEY, json.dumps(wishlist))


def show_home_favorite_toast(message):
    global favorite_toast_timer

    status = document.querySelector("#featured-products-status")
    if status is None:
        section = document.querySelector(".featured-products")
        if section is None:
            return
        status = document.createElement("p")
        status.id = "featured-products-status"
        status.className = "featured-products-status"
        status.setAttribute("role", "status")
        status.setAttribute("aria-live", "polite")
        section.append(status)

    status.textContent = message
    status.hidden = False
    status.classList.add("is-toast", "is-visible")
    if favorite_toast_timer is not None:
        window.clearTimeout(favorite_toast_timer)

    def hide_toast():
        status.classList.remove("is-visible")
        status.remove()

    proxy = create_proxy(hide_toast)
    favorite_callbacks.append(proxy)
    favorite_toast_timer = window.setTimeout(proxy, 2500)


def update_wishlist_empty_state():
    grid = document.querySelector("#wishlist-grid")
    empty_state = document.querySelector("#wishlist-empty")
    if grid is not None and empty_state is not None:
        empty_state.hidden = len(grid.children) > 0


def handle_favorite_click(event):
    favorite_button = event.target.closest(".favorite-button")
    if favorite_button is not None:
        is_favorite = favorite_button.getAttribute("aria-pressed") != "true"
        card = favorite_button.closest(".product-card")
        product_id = card.getAttribute("data-product-id")
        wishlist = load_wishlist()
        if is_favorite:
            wishlist.setdefault(product_id, 1)
        else:
            wishlist.pop(product_id, None)
        save_wishlist(wishlist)
        favorite_button.setAttribute("aria-pressed", str(is_favorite).lower())
        favorite_button.setAttribute(
            "aria-label",
            "Remove from favorites" if is_favorite else "Add to favorites",
        )
        favorite_button.querySelector(".favorite-icon").setAttribute(
            "src",
            f"{STORE_ASSET_DIRECTORY}{'favorite_2.svg' if is_favorite else 'favorite.svg'}",
        )
        if card.closest("#featured-products-grid") is not None:
            show_home_favorite_toast(
                f"{card.getAttribute('data-name')} "
                f"{'added to' if is_favorite else 'removed from'} favorites."
            )
        if document.querySelector("#wishlist-grid") is not None and not is_favorite:
            card.remove()
            update_wishlist_empty_state()
        return

    quantity_button = event.target.closest("[data-quantity-change]")
    if quantity_button is not None:
        card = quantity_button.closest(".product-card")
        product_id = card.getAttribute("data-product-id")
        wishlist = load_wishlist()
        quantity = int(wishlist[product_id])
        quantity = max(
            1, quantity + int(quantity_button.getAttribute("data-quantity-change"))
        )
        wishlist[product_id] = quantity
        save_wishlist(wishlist)
        card.querySelector(".quantity-value").textContent = str(quantity)
        card.querySelector('[data-quantity-change="-1"]').disabled = quantity == 1
        return

    favorite_button = event.target.closest("#detail-favorite")
    if favorite_button is not None:
        is_favorite = favorite_button.getAttribute("aria-pressed") != "true"
        product_id = document.querySelector("#product-detail").getAttribute(
            "data-product-id"
        )
        wishlist = load_wishlist()
        if is_favorite:
            wishlist.setdefault(product_id, 1)
        else:
            wishlist.pop(product_id, None)
        save_wishlist(wishlist)
        favorite_button.setAttribute("aria-pressed", str(is_favorite).lower())
        favorite_button.textContent = "Favourite ♥" if is_favorite else "Favourite ♡"


document.addEventListener("click", create_proxy(handle_favorite_click))