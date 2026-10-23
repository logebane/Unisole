import asyncio
import json

from js import document, window
from pyodide.ffi import create_proxy
from pyodide.http import pyfetch


CART_STORAGE_KEY = "unisole-cart"
DELIVERY_FEE = 0
PAGE_DIRECTORY = str(window.location.pathname).rsplit("/", 1)[0]
RESOURCE_PREFIX = "../" if PAGE_DIRECTORY.endswith("/html") else ""
IMAGE_DIRECTORY = f"{RESOURCE_PREFIX}product_images/"
pending_removal_id = None


def load_cart():
    stored_value = window.localStorage.getItem(CART_STORAGE_KEY)
    if stored_value is None:
        return {}
    cart = json.loads(str(stored_value))
    if not isinstance(cart, dict):
        raise ValueError("Stored cart data must be a JSON object.")
    for product_id, quantity in cart.items():
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            raise ValueError(f"Invalid cart quantity for {product_id}.")
    return cart


def save_cart(cart):
    window.localStorage.setItem(CART_STORAGE_KEY, json.dumps(cart))


def money(amount):
    return f"₱{amount:,.2f}"


def render_cart(shoes):
    cart = load_cart()
    products = {shoe["id"]: shoe for shoe in shoes}
    bag_items = document.querySelector("#bag-items")
    subtotal = 0
    has_unknown_price = False

    for product_id, quantity in cart.items():
        shoe = products.get(product_id)
        if shoe is None:
            raise ValueError(f"Cart item {product_id} is not in the shoe catalog.")

        item = document.createElement("article")
        item.className = "bag-item"
        item.setAttribute("data-product-id", product_id)

        image = document.createElement("img")
        image.className = "bag-item-image"
        image.src = IMAGE_DIRECTORY + shoe["images"][0]
        image.alt = shoe["name"]
        image.loading = "lazy"
        item.append(image)

        details = document.createElement("div")
        name = document.createElement("h3")
        name.className = "bag-item-name"
        name.textContent = shoe["name"]
        category = document.createElement("p")
        category.className = "bag-item-category"
        category.textContent = shoe["category"]
        price = document.createElement("p")
        price.className = "bag-item-price"
        if shoe["price"] is None:
            price.textContent = "Price not set"
            has_unknown_price = True
        else:
            price.textContent = money(shoe["price"])
            subtotal += shoe["price"] * quantity
        details.append(name, category, price)
        item.append(details)

        controls = document.createElement("div")
        controls.className = "bag-item-controls"
        decrease = document.createElement("button")
        decrease.className = "bag-quantity-button"
        decrease.type = "button"
        decrease.textContent = "−"
        decrease.setAttribute("data-quantity-change", "-1")
        decrease.setAttribute("aria-label", f"Decrease {shoe['name']} quantity")
        increase = document.createElement("button")
        increase.className = "bag-quantity-button"
        increase.type = "button"
        increase.textContent = "+"
        increase.setAttribute("data-quantity-change", "1")
        increase.setAttribute("aria-label", f"Increase {shoe['name']} quantity")
        quantity_value = document.createElement("span")
        quantity_value.className = "bag-quantity"
        quantity_value.textContent = str(quantity)
        remove = document.createElement("button")
        remove.className = "bag-remove-button"
        remove.type = "button"
        remove.textContent = "Remove"
        remove.setAttribute("data-remove-item", "")
        remove.setAttribute("aria-label", f"Remove {shoe['name']} from bag")
        controls.append(decrease, quantity_value, increase, remove)
        item.append(controls)
        bag_items.append(item)

    is_empty = not cart
    document.querySelector("#checkout-empty").hidden = not is_empty
    document.querySelector("#bag-subtotal").textContent = (
        "—" if is_empty or has_unknown_price else money(subtotal)
    )
    document.querySelector("#bag-delivery").textContent = (
        "—" if is_empty else money(DELIVERY_FEE)
    )
    document.querySelector("#bag-total").textContent = (
        "—"
        if is_empty or has_unknown_price
        else money(subtotal + DELIVERY_FEE)
    )


def remove_cart_item(product_id):
    cart = load_cart()
    cart.pop(product_id, None)
    save_cart(cart)
    bag_items = document.querySelector("#bag-items")
    bag_items.replaceChildren()
    render_cart(shoes_data)


async def load_shoes():
    response = await pyfetch(f"{RESOURCE_PREFIX}data/shoes.json")
    if not response.ok:
        raise RuntimeError(f"Could not load shoe data (HTTP {response.status}).")
    return json.loads(await response.string())


def handle_cart_click(event):
    button = event.target.closest("[data-quantity-change], [data-remove-item]")
    if button is None:
        return

    item = button.closest(".bag-item")
    product_id = item.getAttribute("data-product-id")
    if button.hasAttribute("data-remove-item"):
        global pending_removal_id
        pending_removal_id = product_id
        document.querySelector("#remove-item-name").textContent = (
            item.querySelector(".bag-item-name").textContent
        )
        document.querySelector("#remove-item-dialog").showModal()
        return

    cart = load_cart()
    cart[product_id] = max(
        1,
        cart[product_id] + int(button.getAttribute("data-quantity-change")),
    )
    save_cart(cart)
    bag_items = document.querySelector("#bag-items")
    bag_items.replaceChildren()
    render_cart(shoes_data)


def handle_remove_confirmation(_event):
    global pending_removal_id
    product_id = pending_removal_id
    pending_removal_id = None
    document.querySelector("#remove-item-dialog").close()
    if product_id is not None:
        remove_cart_item(product_id)


def handle_remove_cancel(_event):
    global pending_removal_id
    pending_removal_id = None
    document.querySelector("#remove-item-dialog").close()


async def initialize():
    status = document.querySelector("#checkout-status")
    try:
        global shoes_data
        shoes_data = await load_shoes()
        render_cart(shoes_data)
        document.querySelector("#bag-items").addEventListener(
            "click", create_proxy(handle_cart_click)
        )
        document.querySelector("#cancel-remove-item").addEventListener(
            "click", create_proxy(handle_remove_cancel)
        )
        document.querySelector("#remove-item-dialog").addEventListener(
            "cancel", create_proxy(handle_remove_cancel)
        )
        document.querySelector("#confirm-remove-item").addEventListener(
            "click", create_proxy(handle_remove_confirmation)
        )
    except Exception as error:
        status.textContent = f"Unable to load your bag: {error}"
        status.hidden = False
        raise


asyncio.ensure_future(initialize())