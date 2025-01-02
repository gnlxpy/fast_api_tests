def hello():
    return print('Hello World!')

def say(msg : str) -> bool:
    if len(msg) < 20:
        print(msg)
        return True
    else:
        print(f'message is big!')
        return False
