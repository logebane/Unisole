import json
import random

from js import document, window
from pyodide.ffi import create_proxy


PAGE_DIRECTORY = str(window.location.pathname).rsplit("/", 1)[0]
RESOURCE_PREFIX = "../" if PAGE_DIRECTORY.endswith("/html") else ""
IMAGE_DIRECTORY = f"{RESOURCE_PREFIX}product_images/"
CART_STORAGE_KEY = "unisole-cart"
WISHLIST_STORAGE_KEY = "unisole-wishlist"


def load_storage_map(key):
    stored_value = window.localStorage.getItem(key)
    if stored_value is None:
        return {}

    values = json.loads(str(stored_value))
    if not isinstance(values, dict):
        raise ValueError(f"Stored {key} data must be a JSON object.")
    return values


def save_storage_map(key, values):
    window.localStorage.setItem(key, json.dumps(values))


def finish_wishlist_card_removal(event):
    card = event.target
    if event.animationName != "wishlist-card-slide-right":
        return

    card.remove()
    grid = document.querySelector("#wishlist-grid")
    empty_state = document.querySelector("#wishlist-empty")
    if grid is not None and empty_state is not None:
        empty_state.hidden = len(grid.children) > 0


def show_preview(preview_button, animate=False):
    card = preview_button.closest(".product-card")
    image = card.querySelector(".product-image")
    image.src = f"{IMAGE_DIRECTORY}{preview_button.getAttribute('data-image')}"
    image.alt = preview_button.getAttribute("data-name")
    if animate:
        image.classList.remove("mobile-image-transition")
        image.offsetWidth
        image.classList.add("mobile-image-transition")
    for option in card.querySelectorAll(".preview-option"):
        option.setAttribute("aria-pressed", str(option == preview_button).lower())


def restore_original_image(event):
    card = event.target.closest(".product-card")
    if card is None:
        return

    next_target = event.relatedTarget
    if next_target is not None and card.contains(next_target):
        return

    image = card.querySelector(".product-image")
    image.src = f"{IMAGE_DIRECTORY}{image.getAttribute('data-original-image')}"
    image.alt = image.getAttribute("data-original-name")
    for option in card.querySelectorAll(".preview-option"):
        is_original = option.getAttribute("data-image") == image.getAttribute(
            "data-original-image"
        )
        option.setAttribute("aria-pressed", str(is_original).lower())


def handle_catalog_click(event):
    preview_button = event.target.closest(".preview-option")
    if preview_button is not None:
        product_url = preview_button.getAttribute("data-product-url")
        if product_url:
            window.location.href = product_url
        return

    add_to_cart_button = event.target.closest(".wishlist-add-to-cart")
    if add_to_cart_button is not None:
        card = add_to_cart_button.closest(".product-card")
        if card.classList.contains("wishlist-card-slide-out"):
            return

        product_id = card.getAttribute("data-product-id")
        quantity = int(card.querySelector(".quantity-value").textContent)
        cart = load_storage_map(CART_STORAGE_KEY)
        cart[product_id] = int(cart.get(product_id, 0)) + quantity
        save_storage_map(CART_STORAGE_KEY, cart)

        wishlist_grid = document.querySelector("#wishlist-grid")
        if wishlist_grid is not None and wishlist_grid.contains(card):
            wishlist = load_storage_map(WISHLIST_STORAGE_KEY)
            wishlist.pop(product_id, None)
            save_storage_map(WISHLIST_STORAGE_KEY, wishlist)
            if window.matchMedia("(prefers-reduced-motion: reduce)").matches:
                card.remove()
                empty_state = document.querySelector("#wishlist-empty")
                if empty_state is not None:
                    empty_state.hidden = len(wishlist_grid.children) > 0
            else:
                card.classList.add("wishlist-card-slide-out")

        status = document.querySelector("#wishlist-status")
        if status is not None:
            status.textContent = (
                f"Added {quantity} × {card.getAttribute('data-name')} to bag."
            )
            status.hidden = False
            status.style.animation = "none"
            status.offsetWidth
            status.style.animation = ""
        return


def handle_detail_click(event):
    size_button = event.target.closest(".size-option")
    if size_button is not None:
        for option in document.querySelectorAll(".size-option"):
            option.setAttribute("aria-pressed", str(option == size_button).lower())
        document.querySelector("#product-action-status").textContent = ""
        return

    thumbnail = event.target.closest(".product-thumbnail")
    if thumbnail is not None:
        main_image = document.querySelector("#gallery-main-image")
        main_image.src = f"{IMAGE_DIRECTORY}{thumbnail.getAttribute('data-image')}"
        for option in document.querySelectorAll(".product-thumbnail"):
            option.setAttribute("aria-pressed", str(option == thumbnail).lower())
        return

    add_button = event.target.closest("#add-to-bag")
    if add_button is not None:
        selected_size = next(
            (
                option.getAttribute("data-size")
                for option in document.querySelectorAll(".size-option")
                if option.getAttribute("aria-pressed") == "true"
            ),
            None,
        )
        status = document.querySelector("#product-action-status")
        if selected_size is None:
            status.textContent = "Please select a size first."
            return
        product_id = document.querySelector("#product-detail").getAttribute(
            "data-product-id"
        )
        cart = load_storage_map(CART_STORAGE_KEY)
        cart[product_id] = int(cart.get(product_id, 0)) + 1
        save_storage_map(CART_STORAGE_KEY, cart)
        status.textContent = ""
        for option in document.querySelectorAll(".size-option"):
            option.setAttribute("aria-pressed", "false")

        product_name = document.querySelector("#detail-name").textContent
        document.querySelector("#bag-added-message").textContent = (
            f"{product_name} (size {selected_size}) was added to your bag."
        )
        document.querySelector("#bag-added-dialog").showModal()


def close_bag_added_dialog(_event):
    document.querySelector("#bag-added-dialog").close()


def handle_preview_hover(event):
    preview_button = event.target.closest(".preview-option")
    if preview_button is not None:
        previous_target = event.relatedTarget
        if previous_target is not None and preview_button.contains(previous_target):
            return
        show_preview(preview_button)


def rotate_card_preview(card):
    if (
        document.hidden
        or card.hidden
        or not window.matchMedia("(max-width: 640px)").matches
    ):
        return

    options = list(card.querySelectorAll(".preview-option"))
    if len(options) < 2:
        return

    image = card.querySelector(".product-image")
    current_image = image.getAttribute("src").rsplit("/", 1)[-1]
    alternatives = [
        option
        for option in options
        if option.getAttribute("data-image") != current_image
    ]
    if alternatives:
        show_preview(random.choice(alternatives), animate=True)


active_card_timers = {}
visible_cards = {}


def stop_card_timer(card_id):
    timer = active_card_timers.pop(card_id, None)
    if timer is not None:
        window.clearInterval(timer[0])


def start_card_timer(card_id, card):
    if card_id in active_card_timers or card.hidden:
        return

    timer_callback = create_proxy(lambda: rotate_card_preview(card))
    interval_id = window.setInterval(timer_callback, 4000)
    active_card_timers[card_id] = (interval_id, timer_callback)


def sync_visible_card_timers(_event=None):
    should_run = (
        not document.hidden
        and window.matchMedia("(max-width: 640px)").matches
    )
    if not should_run:
        for card_id in list(active_card_timers):
            stop_card_timer(card_id)
        return

    for card_id, card in visible_cards.items():
        start_card_timer(card_id, card)


def on_cards_intersect(entries, _observer):
    for entry in entries:
        card = entry.target
        card_id = card.getAttribute("data-catalog-index")
        if entry.isIntersecting and not card.hidden:
            visible_cards[card_id] = card
        else:
            visible_cards.pop(card_id, None)
            stop_card_timer(card_id)
    sync_visible_card_timers()


shoe_grid = document.querySelector("#shoe-grid")
wishlist_grid = document.querySelector("#wishlist-grid")
for catalog_grid in (shoe_grid, wishlist_grid):
    if catalog_grid is not None:
        catalog_grid.addEventListener("click", create_proxy(handle_catalog_click))

if wishlist_grid is not None:
    wishlist_grid.addEventListener(
        "animationend", create_proxy(finish_wishlist_card_removal)
    )

if shoe_grid is not None:
    shoe_grid.addEventListener("mouseover", create_proxy(handle_preview_hover))
    shoe_grid.addEventListener("mouseout", create_proxy(restore_original_image))
    mobile_preview_state_handler = create_proxy(sync_visible_card_timers)
    window.addEventListener("resize", mobile_preview_state_handler)
    document.addEventListener("visibilitychange", mobile_preview_state_handler)
    intersection_handler = create_proxy(on_cards_intersect)
    card_observer = window.IntersectionObserver.new(
        intersection_handler, {"threshold": 0.1}
    )

    def observe_catalog_cards(_event=None):
        for card in shoe_grid.querySelectorAll(".product-card"):
            card_observer.observe(card)

    catalog_ready_handler = create_proxy(observe_catalog_cards)
    document.addEventListener("shoe-catalog-ready", catalog_ready_handler)
    observe_catalog_cards()
    sync_visible_card_timers()

if document.querySelector("#product-detail") is not None:
    document.addEventListener("click", create_proxy(handle_detail_click))
    document.querySelector("#close-bag-added-dialog").addEventListener(
        "click", create_proxy(close_bag_added_dialog)
    )
