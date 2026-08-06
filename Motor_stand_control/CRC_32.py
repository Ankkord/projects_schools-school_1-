import binascii
import zlib
import timeit
import random
import string

class CRC32:
    def __init__(self, poly=0xEDB88320, init_value=0xFFFFFFFF):
        """
        Инициализация CRC32 с использованием заданного полинома и начального значения.
        """
        # todo: попробовать применить какую-то библиотеку
        self.poly = poly
        self.init_value = init_value
        self.crc_val = init_value
        self.table = self._generate_table()

    def _generate_table(self):
        """
        Генерация таблицы CRC32.
        """
        table = []
        for byte in range(256):
            crc = byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ self.poly
                else:
                    crc >>= 1
            table.append(crc)
        return table

    def reset(self):
        """
        Сброс CRC к начальному значению.
        """
        self.crc_val = self.init_value

    def get_val(self):
        """
        Возвращает накопленное значение CRC.
        """
        return self.crc_val ^ 0xFFFFFFFF

    def set_val(self, value):
        """
        Устанавливает заданное значение CRC.
        """
        self.crc_val = value

    def calc(self, data: bytes) -> int:
        crc = self.init_value
        # print("Generated packet in hex:", " ".join(f"{byte:02X}" for byte in data))
        for byte in data:
            # Обрезаем до 32 бит после каждой операции
            crc = self.table[(crc ^ byte) & 0xFF] ^ (crc >> 8)
            crc &= 0xFFFFFFFF  # Обрезаем до 32 бит
        return crc ^ 0xFFFFFFFF  # Инверсия результата

    def calc_reversed(self, data: bytes) -> int:
        """
        Вычисляет CRC с инверсией порядка байтов результата.
        """
        crc = self.calc(data)
        # Инвертируем порядок байтов результата
        return int.from_bytes(crc.to_bytes(4, byteorder="big"), byteorder="little")

    def acc(self, data: bytes) -> int:
        """
        Накопительно вычисляет CRC32 для данных.
        """
        for byte in data:
            self.crc_val = self.table[(self.crc_val ^ byte) & 0xFF] ^ (self.crc_val >> 8)
        return self.crc_val ^ 0xFFFFFFFF

def test_speed():
    crc32 = CRC32()
    size_mb = 1
    def generate_data(size: int = size_mb * 1024 * 1024) -> bytes:
        """Генерирует случайные байты заданного размера (по умолчанию 100 МБ)."""
        return ''.join(random.choice(string.ascii_letters + string.digits)
                       for _ in range(size)).encode('utf-8')

    def test_custom():
        data = generate_data()
        return crc32.calc(data)

    def test_binascii():
        data = generate_data()
        return binascii.crc32(data)

    def test_zlib():
        data = generate_data()
        return zlib.crc32(data)

    # ---------- Проверка корректности ----------
    small = b"12345678"
    print("Проверка на маленькой строке:")
    print(f"Custom:    {crc32.calc(small)}")
    print(f"binascii:  {binascii.crc32(small)}")
    print(f"zlib:      {zlib.crc32(small)}")

    # ---------- Тест производительности ----------
      # размер данных в МБ
    repeats = 5  # сколько раз прогоняем каждую функцию

    time_custom = timeit.timeit(test_custom, number=repeats)
    time_binascii = timeit.timeit(test_binascii, number=repeats)
    time_zlib = timeit.timeit(test_zlib, number=repeats)

    total_mb = size_mb * repeats

    print(f"\nТест на {size_mb} МБ × {repeats} = {total_mb} МБ данных:")
    print(f"Custom CRC32 (pure Python): {time_custom:.2f} сек")
    print(f"binascii.crc32:             {time_binascii:.2f} сек")
    print(f"zlib.crc32:                 {time_zlib:.2f} сек")

    print(f"\nСкорость (МБ/с):")
    print(f"Custom:    {total_mb / time_custom:.2f}")
    print(f"binascii:  {total_mb / time_binascii:.2f}")
    print(f"zlib:      {total_mb / time_zlib:.2f}")

def main():
    ...

if __name__ == "__main__":
    test_speed()


