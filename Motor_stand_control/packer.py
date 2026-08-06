PTPP2_DELIMITER_BYTE = 0x7D
PTPP2_ESCAPE_BYTE = 0x7E
PTPP2_ESCAPE_MASK = 0x20
PTPP2_MAX_CMD_LEN = 1024  # Максимальная длина команды, значение примерное
PTPP2_MAX_LEN_WS = 2048  # Максимальная длина буфера с разделителями, значение примерное
PTPP2_MAX_LEN_WOS = 1024  # Максимальная длина буфера без разделителей, значение примерное

import zlib



def calculate_crc(data: bytes) -> int:
    return zlib.crc32(data)


def copy_with_byte_stuffing(src: bytes) -> bytes:
    """
    Копирование данных с применением байтстаффинга.
    """
    dest = bytearray()

    for byte in src:
        if byte in (PTPP2_DELIMITER_BYTE, PTPP2_ESCAPE_BYTE):
            dest.append(PTPP2_ESCAPE_BYTE)
            dest.append(byte ^ PTPP2_ESCAPE_MASK)
        else:
            dest.append(byte)

    return bytes(dest)

def pack_data(data: bytes, tx_seq_number: int) -> bytes:
    """
    Формирует пакет данных с байтстаффингом и CRC.
    """
    if len(data) == 0 or len(data) > PTPP2_MAX_CMD_LEN:
        raise ValueError("Invalid data length")

    # Смещение
    shift = PTPP2_MAX_LEN_WS - PTPP2_MAX_LEN_WOS

    # Формируем пакет без байтстаффинга
    tx_buffer = bytearray(PTPP2_MAX_LEN_WS)
    ind = shift

    # Добавляем порядковый номер пакета
    tx_buffer[ind] = tx_seq_number
    ind += 1

    # Копируем данные
    tx_buffer[ind:ind + len(data)] = data
    ind += len(data)

    # Учитываем порядковый номер команды в длине
    packet_len = len(data) + 1

    # Вычисляем CRC
    crc = calculate_crc(tx_buffer[shift:shift + packet_len])
    tx_buffer[ind:ind + 4] = crc.to_bytes(4, byteorder='little')
    ind += 4

    # Учитываем длину CRC
    packet_len += 4

    # Формируем пакет с байтстаффингом
    stuffed_data = copy_with_byte_stuffing(tx_buffer[shift:shift + packet_len])

    # Добавляем разделительные байты
    final_packet = bytearray()
    final_packet.append(PTPP2_DELIMITER_BYTE)
    final_packet.extend(stuffed_data)
    final_packet.append(PTPP2_DELIMITER_BYTE)

    return bytes(final_packet)

def remove_byte_stuffing(data: bytes) -> bytes:
    """
    Выполняет обратное преобразование байтстаффинга.
    """
    unstuffed = bytearray()
    escape_next = False

    for byte in data:
        if escape_next:
            unstuffed.append(byte ^ PTPP2_ESCAPE_MASK)
            escape_next = False
        elif byte == PTPP2_ESCAPE_BYTE:
            escape_next = True
        else:
            unstuffed.append(byte)

    if escape_next:
        raise ValueError("Invalid byte-stuffing: escape byte at the end")

    return bytes(unstuffed)

def unpack_data(packet: bytes) -> bytes:
    """
    Выполняет обратные преобразования для пакета:
    - Удаляет разделительные байты
    - Выполняет обратный байтстаффинг
    - Проверяет CRC
    - Возвращает полезные данные
    """
    # Проверяем минимальную длину пакета (разделители + минимальные данные)
    if len(packet) < 2:
        raise ValueError("Invalid packet length")

    # Убираем разделительные байты
    if packet[0] != PTPP2_DELIMITER_BYTE or packet[-1] != PTPP2_DELIMITER_BYTE:
        raise ValueError("Packet does not start or end with the delimiter byte")

    stuffed_data = packet[1:-1]

    # Выполняем обратный байтстаффинг
    unstuffed_data = remove_byte_stuffing(stuffed_data)

    # Проверяем минимальную длину после удаления байтстаффинга (seq_number + CRC)
    if len(unstuffed_data) < 5:
        raise ValueError("Unstuffed packet is too short")

    # Выделяем данные и CRC
    seq_number = unstuffed_data[0]
    data = unstuffed_data[1:-4]
    received_crc = int.from_bytes(unstuffed_data[-4:], byteorder='little')

    # Проверяем CRC
    calculated_crc = calculate_crc(unstuffed_data[:-4])
    if calculated_crc != received_crc:
        raise ValueError("CRC mismatch")

    # Возвращаем полезные данные (без порядкового номера пакета)
    return data





if __name__ == '__main__':
    # Создаем бинарные данные
    test_data = bytes([0x45, 0xe4, 0x03, 0x20, 0x7D, 0x7E])
    packet = pack_data(test_data, 0x00)  # Формируем пакет

    # Печатаем результат в формате hex
    print("Generated packet in hex:", " ".join(f"{byte:02X}" for byte in packet))
