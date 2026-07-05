def cart_summary(request):
    customer = getattr(request.user, "customer_profile", None)
    if not request.user.is_authenticated or customer is None:
        return {"cart_item_count": 0}

    cart = getattr(customer, "cart", None)
    if cart is None:
        return {"cart_item_count": 0}

    return {"cart_item_count": cart.item_count}
