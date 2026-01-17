import tiktoken

enc = tiktoken.get_encoding("cl100k_base")
noise_unit = "NOISE_BUFFER "
count_1 = len(enc.encode(noise_unit))
count_4000 = len(enc.encode(noise_unit * 4000))
count_5000 = len(enc.encode(noise_unit * 5000))

print(f"Unit '{noise_unit}': {count_1} tokens")
print(f"4000 units: {count_4000} tokens")
print(f"5000 units: {count_5000} tokens")
print(f"Chars in 5000 units: {len(noise_unit * 5000)}")
