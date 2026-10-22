import asyncio
import json
from urllib.parse import parse_qs

from js import document, window
from pyodide.http import pyfetch


PAGE_DIRECTORY = str(window.location.pathname).rsplit("/", 1)[0]
RESOURCE_PREFIX = "../" if PAGE_DIRECTORY.endswith("/html") else ""
IMAGE_DIRECTORY = f"{RESOURCE_PREFIX}product_images/"
STORE_ASSET_DIRECTORY = f"{RESOURCE_PREFIX}store_assets/"
WISHLIST_STORAGE_KEY = "unisole-wishlist"


async def load_shoes():
    response = await pyfetch(f"{RESOURCE_PREFIX}data/shoes.json")
    if not response.ok:
        raise RuntimeError(f"Could not load shoe data (HTTP {response.status}).")
    return json.loads(await response.string())


def set_text(selector, value):
    element = document.querySelector(selector)
    if element is not None:
        element.textContent = value


def signal_shoe_data_state(state):
    body = document.body
    body.setAttribute("data-shoe-data-state", state)
    event_name = "shoe-data-ready" if state == "ready" else "shoe-data-error"
    document.dispatchEvent(window.Event.new(event_name))


def load_storage_map(key):
    stored_value = window.localStorage.getItem(key)
    if stored_value is None:
        return {}

    values = json.loads(str(stored_value))
    if not isinstance(values, dict):
        raise ValueError(f"Stored {key} data must be a JSON object.")
    return values


def render_shoe_card(shoe, wishlist, catalog_index, return_to_home, show_previews):
    template = document.querySelector("#shoe-card-template")
    card = template.content.cloneNode(True)
    card_element = card.querySelector(".product-card")
    card_element.setAttribute("data-product-id", shoe["id"])
    card_element.setAttribute("data-name", shoe["name"])
    card_element.setAttribute(
        "data-price", "" if shoe["price"] is None else str(shoe["price"])
    )
    card_element.setAttribute("data-tags", json.dumps(shoe.get("tags", {})))
    card_element.setAttribute("data-catalog-index", str(catalog_index))
    favorite_button = card.querySelector(".favorite-button")
    is_favorite = shoe["id"] in wishlist
    favorite_button.setAttribute("aria-pressed", str(is_favorite).lower())
    favorite_button.setAttribute(
        "aria-label",
        "Remove from favorites" if is_favorite else "Add to favorites",
    )
    card.querySelector(".favorite-icon").setAttribute(
        "src",
        f"{STORE_ASSET_DIRECTORY}{'favorite_2.svg' if is_favorite else 'favorite.svg'}",
    )
    image = card.querySelector(".product-image")
    image.src = IMAGE_DIRECTORY + shoe["images"][0]
    image.alt = shoe["name"]
    image.setAttribute("data-original-image", shoe["images"][0])
    image.setAttribute("data-original-name", shoe["name"])

    return_location = "&from=home" if return_to_home else ""
    product_url = f"product_preview.html?id={shoe['id']}{return_location}"
    product_link = card.querySelector(".product-image-link")
    product_link.href = product_url
    product_link.setAttribute("aria-label", f"View details for {shoe['name']}")
    name_link = card.querySelector(".product-name-link")
    name_link.href = product_url
    name_link.textContent = shoe["name"]
    card.querySelector(".product-price").textContent = (
        f"₱{shoe['price']:,.2f}" if shoe["price"] is not None else "Price not set"
    )
    card.querySelector(".product-category").textContent = shoe["category"]

    quantity_value = card.querySelector(".quantity-value")
    if quantity_value is not None:
        quantity = wishlist[shoe["id"]]
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            raise ValueError(f"Invalid wishlist quantity for {shoe['id']}.")
        quantity_value.textContent = str(quantity)
        card.querySelector('[data-quantity-change="-1"]').disabled = quantity <= 1

    preview_selector = card.querySelector(".product-preview-selector")
    if not show_previews or len(shoe["images"]) < 2:
        if preview_selector is not None:
            preview_selector.remove()
    elif preview_selector is not None:
        for preview_index, image_name in enumerate(shoe["images"]):
            preview_button = document.createElement("button")
            preview_button.type = "button"
            preview_button.className = "preview-option"
            preview_button.setAttribute(
                "aria-pressed", str(preview_index == 0).lower()
            )
            preview_button.setAttribute(
                "aria-label", f"Preview {shoe['name']} image {preview_index + 1}"
            )
            preview_button.setAttribute("data-image", image_name)
            preview_button.setAttribute("data-name", shoe["name"])
            preview_button.setAttribute(
                "data-product-url", product_link.getAttribute("href")
            )

            preview_thumbnail = document.createElement("img")
            preview_thumbnail.src = IMAGE_DIRECTORY + image_name
            preview_thumbnail.alt = ""
            preview_thumbnail.loading = "lazy"
            preview_button.append(preview_thumbnail)
            preview_selector.append(preview_button)

    return card


def render_shoe_grid(
    shoes, shoe_grid, wishlist, return_to_home=False, show_previews=True
):
    for shoe in shoes:
        card = render_shoe_card(
            shoe,
            wishlist,
            len(shoe_grid.children),
            return_to_home,
            show_previews,
        )
        shoe_grid.append(card)


def render_catalog(shoes):
    shoe_grid = document.querySelector("#shoe-grid")
    wishlist = load_storage_map(WISHLIST_STORAGE_KEY)
    render_shoe_grid(shoes, shoe_grid, wishlist)
    document.dispatchEvent(window.Event.new("shoe-catalog-ready"))


def render_home_catalog(shoes):
    shoe_grid = document.querySelector("#featured-products-grid")
    wishlist = load_storage_map(WISHLIST_STORAGE_KEY)
    render_shoe_grid(
        shoes[:4],
        shoe_grid,
        wishlist,
        return_to_home=True,
        show_previews=False,
    )


def render_wishlist(shoes):
    shoe_grid = document.querySelector("#wishlist-grid")
    wishlist = load_storage_map(WISHLIST_STORAGE_KEY)
    wishlist_shoes = [shoe for shoe in shoes if shoe["id"] in wishlist]
    render_shoe_grid(wishlist_shoes, shoe_grid, wishlist)

    empty_state = document.querySelector("#wishlist-empty")
    if empty_state is not None:
        empty_state.hidden = len(shoe_grid.children) > 0


def render_product(shoes):
    query = parse_qs(str(window.location.search).lstrip("?"))
    shoe_id = query.get("id", [None])[0]
    return_to_home = query.get("from", [None])[0] == "home"
    back_url = "index.html" if return_to_home else "product_lineup_page.html"
    back_label = "Back to home" if return_to_home else "Back to shoes"
    back_button = document.querySelector(".product-back-button")
    back_button.href = back_url
    back_button.setAttribute("aria-label", back_label)
    back_button.querySelector("span:last-child").textContent = (
        "Home" if return_to_home else "Back"
    )
    not_found_link = document.querySelector("#product-not-found a")
    not_found_link.href = back_url
    not_found_link.textContent = back_label

    shoe = next((item for item in shoes if item["id"] == shoe_id), None)
    if shoe is None:
        document.querySelector("#product-not-found").hidden = False
        return

    document.querySelector("#product-detail").hidden = False
    document.querySelector("#product-detail").setAttribute("data-product-id", shoe["id"])
    set_text("#detail-name", shoe["name"])
    set_text("#detail-category", shoe["category"])
    set_text(
        "#detail-price",
        f"₱{shoe['price']:,.2f}" if shoe["price"] is not None else "Price not set",
    )
    main_image = document.querySelector("#gallery-main-image")
    main_image.src = IMAGE_DIRECTORY + shoe["images"][0]
    main_image.alt = shoe["name"]
    favorite_button = document.querySelector("#detail-favorite")
    is_favorite = shoe["id"] in load_storage_map(WISHLIST_STORAGE_KEY)
    favorite_button.setAttribute("aria-pressed", str(is_favorite).lower())
    favorite_button.textContent = "Favourite ♥" if is_favorite else "Favourite ♡"

    thumbnails = document.querySelector("#product-thumbnails")
    for image_index, image_name in enumerate(shoe["images"]):
        thumbnail = document.createElement("button")
        thumbnail.type = "button"
        thumbnail.className = "product-thumbnail"
        thumbnail.setAttribute("data-image", image_name)
        thumbnail.setAttribute("aria-label", f"Show {shoe['name']} image {image_index + 1}")
        thumbnail.setAttribute("aria-pressed", str(image_index == 0).lower())
        thumbnail_image = document.createElement("img")
        thumbnail_image.src = IMAGE_DIRECTORY + image_name
        thumbnail_image.alt = ""
        thumbnail.append(thumbnail_image)
        thumbnails.append(thumbnail)

    sizes = document.querySelector("#size-options")
    for size in shoe["sizes"]:
        size_button = document.createElement("button")
        size_button.type = "button"
        size_button.className = "size-option"
        size_button.textContent = size
        size_button.setAttribute("data-size", size)
        size_button.setAttribute("aria-pressed", "false")
        sizes.append(size_button)


async def initialize():
    try:
        shoes = await load_shoes()
        if document.querySelector("#featured-products-grid") is not None:
            render_home_catalog(shoes)
            status = document.querySelector("#data-status")
            if status is not None:
                status.hidden = True
        elif document.querySelector("#shoe-grid") is not None:
            render_catalog(shoes)
            status = document.querySelector("#data-status")
            if status is not None:
                status.hidden = True
        elif document.querySelector("#wishlist-grid") is not None:
            render_wishlist(shoes)
            status = document.querySelector("#data-status")
            if status is not None:
                status.hidden = True
        elif document.querySelector("#product-detail") is not None:
            status = document.querySelector("#data-status")
            if status is not None:
                status.hidden = True
            document.querySelector("#product-detail").hidden = True
            render_product(shoes)
    except Exception as error:
        status = document.querySelector("#data-status")
        if status is None:
            status = document.querySelector("#featured-products-status")
        if status is None:
            section = document.querySelector(".featured-products")
            if section is not None:
                status = document.createElement("p")
                status.id = "featured-products-status"
                status.className = "featured-products-status"
                status.setAttribute("role", "status")
                status.setAttribute("aria-live", "polite")
                section.append(status)
        if status is not None:
            status.textContent = f"Unable to load shoe information: {error}"
            status.hidden = False
        signal_shoe_data_state("error")
        raise

    signal_shoe_data_state("ready")

asyncio.ensure_future(initialize())
