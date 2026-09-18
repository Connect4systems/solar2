"""Recover UTF-8 text mistakenly decoded as Windows-1252/Latin-1.

Only reversible, valid UTF-8 byte sequences are changed. Correct Arabic and
standalone Western characters are preserved; no replacement characters are used.
"""


def _byte(character):
	try:
		return character.encode("cp1252")[0]
	except UnicodeEncodeError:
		return ord(character) if ord(character) <= 255 else None


def repair_text(value):
	for _ in range(4):
		result = []
		index = 0
		while index < len(value):
			first = _byte(value[index])
			width = 0
			if first is not None:
				if 0xC2 <= first <= 0xDF:
					width = 2
				elif 0xE0 <= first <= 0xEF:
					width = 3
				elif 0xF0 <= first <= 0xF4:
					width = 4
			if width and index + width <= len(value):
				sequence = [_byte(char) for char in value[index : index + width]]
				if all(byte is not None for byte in sequence):
					try:
						decoded = bytes(sequence).decode("utf-8")
					except UnicodeDecodeError:
						pass
					else:
						result.append(decoded)
						index += width
						continue
			result.append(value[index])
			index += 1
		fixed = "".join(result)
		if fixed == value:
			return value
		value = fixed
	return value
