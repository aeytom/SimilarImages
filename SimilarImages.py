#!/usr/local/bin/python3

"""
test detecting near similar images
"""

import os
from hashlib import sha256

import dhash
import PIL
from wand.image import Image

IMAGE_DIR = './cm-assets'


def load_images(directory):
    """
    generate recursive image list from directory
    """
    image_list = []
    # pylint: disable=unused-variable
    for dir_path, dir_names, file_names in os.walk(directory):
        # if (len(image_list) > 1000):
        #     break
        for file in file_names:
            if '_thumb.' in file:
                current_image_name = os.path.join(dir_path, file)
                try:
                    f_p = open(current_image_name, 'r')
                    f_p.close()
                    image_list.append(current_image_name)
                except OSError as os_e:
                    print(os_e)
    return image_list


def split_hash(hex_hash):
    """
    split hex hash in sub keys to build hash lookup keys
    """
    h_list = []
    for offset in range(0, 32, 4):
        h_list.append(str.format("%x:" % offset) + hex_hash[offset:offset+4])
    return h_list


def base_image_name(image_name):
    """
    get file name without path and extension
    """
    return os.path.splitext(os.path.basename(image_name))[0]


def write_dup_image(img1, img2):
    """
    combine two "similar" images to one side-by-side image
    """
    if img1 > img2:
        # swap images to sort the names
        img1, img2 = (img2, img1)
    name = base_image_name(img1)+"-"+base_image_name(img2)
    images = [PIL.Image.open(img1), PIL.Image.open(img2)]
    widths, heights = zip(*(i.size for i in images))
    total_width = sum(widths)
    max_height = max(heights)
    new_im = PIL.Image.new('RGB', (total_width, max_height))
    x_offset = 0
    for im in images:
        new_im.paste(im, (x_offset, 0))
        x_offset += im.size[0]
    new_im.save(name+'.jpg')


def duplicate_key(img1, img2):
    """
    build key for duplicates dict
    """
    if img1 > img2:
        # swap images to sort the names
        img1, img2 = (img2, img1)
    return sha256((str(img1) + ":" + str(img2)).encode('utf-8')).hexdigest()


def image_dhash(image_list, size=8, threshold=4):
    """
    detect duplicates using dhash
    """
    duplicates_dict = {}
    lookup_dict = {}
    images_by_dhash = {}
    for current_image_name in image_list:

        h_row, h_col = dhash.dhash_row_col(
            Image(filename=current_image_name), size=size)
        h_hash = dhash.format_hex(h_row, h_col, size=size)
        i_hash = h_row << (size * size) | h_col
        current_image_is_duplicate = False

        if i_hash in images_by_dhash:
            images_by_dhash[i_hash].append(current_image_name)
        else:
            images_by_dhash[i_hash] = [current_image_name]

        for s_h in split_hash(h_hash):
            if s_h in lookup_dict:
                # lookup existing canditates for similar matching
                for l_hash in lookup_dict[s_h]:
                    if current_image_is_duplicate:
                        break
                    diff_bits = dhash.get_num_bits_different(i_hash, l_hash)
                    if diff_bits <= threshold:
                        # similar match success
                        current_image_is_duplicate = True
                        d_key = duplicate_key(i_hash, l_hash)
                        if d_key not in duplicates_dict:
                            print(current_image_name,
                                  h_hash, l_hash, diff_bits)
                            duplicates_dict[d_key] = (i_hash, l_hash)

            if not current_image_is_duplicate:
                # image is a new candidate for a similar match
                if s_h in lookup_dict:
                    lookup_dict[s_h].append(i_hash)
                else:
                    lookup_dict[s_h] = [i_hash]

    return duplicates_dict, images_by_dhash


os.chdir(IMAGE_DIR)
os.getcwd()

image_files = load_images('.')
print(len(image_files))

duplicates, images_by_dhash = image_dhash(image_files, threshold=8)

print("Dict dhash duplicates:")
for h, dups in duplicates.items():
    dups = images_by_dhash[dups[0]] + images_by_dhash[dups[1]]
    img_last = dups.pop()
    for dup in dups:
        print(img_last, dup)
        write_dup_image(img_last, dup)
