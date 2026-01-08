import random


class NumberHelper:
    @staticmethod
    def get_random_number(digit: int) -> int:
        return random.randint(10 ** (digit - 1), 10**digit - 1)
