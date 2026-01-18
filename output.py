def validate_order(order) if order['price'] < 0:
        raise ValueError('Invalid price')
    if not order['items']:
        raise ValueError('No items')


def process_order(order):
    validate_order(order)
    total = order['price'] * 1.08  # Tax
    print(f'Saving order {order['id']} with total {total}')
    return total