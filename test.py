import re


# link = 'https://i.pximg.net/c/540x540_70/img-master/img/2026/05/15/22/20/47/144811703_p0_master1200.jpg'
# print('/'.join(link.split('/')[:-1]))
text = "user_p1001 and admin_p205"
filename = '144811703_p0_master1200.jpg'
pattern = r'(_p)(\d+)'
matches = re.findall(pattern, filename)
print(matches)
match = re.search(pattern, text)
if match:
    print(match.group(0))
    print(match.group(1))
    print(match.group(2))

replacement = rf'\g<1>{22}'
new_filename = re.sub(pattern, replacement, filename)
print(new_filename)
