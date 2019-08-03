from PIL import Image, ImageDraw
import os
import math

def build_collage(banner=None, target=None, directory=None, border=75, frame_width=6, frame_color=(0,0,0)):
	#print('params: directory={}; banner={}; target={}'.format(directory, banner, args.target))

	# size needs to match printer paper
	# in case of canon cp910: 4 x 6 in (or 100 x 148 mm)
	size = (3800, 2568)
	collage = Image.new('RGB', size, (255, 255, 255))
	if frame_width > 0:
		draw = ImageDraw.Draw(collage)

	images = [os.path.join(directory, p) for p in os.listdir(directory)]
	images.sort(key=lambda s: os.path.getmtime(s))

	banner_size = (int(math.ceil(float(size[0])/8)), size[1] - border*2)

	#print('banner size: {}'.format(banner_size))
	width = int((size[0] - float(banner_size[0])) / 2 - border)
	available_height = (size[1] / 2) - (border/2)

	count_x = 0
	count_y = 0
	banner_y = -1

	for img_path in images:
		img = Image.open(img_path)
		
		w, h = img.size
		aspect_ratio = 1 / (float(w) / float(h))
		height = int(math.ceil(width * aspect_ratio))
		total_height = 3 * border + 2 * height
		if total_height > size[1]:
			# two images are higher than our usable area
			height = int(math.ceil((width - float(width)/10) * aspect_ratio))
			#print('total height={} > full height; new height={}'.format(total_height, height))
		resize_size = (width, height)
		#print('resize_size: {}, w: {}, h: {}, mode: {}, aspect-ratio: {}'.format(resize_size, w, h, img.mode, aspect_ratio))
		resized_img = img.resize(resize_size, Image.LANCZOS)

		offset_y = available_height - height - border + (border/2 if count_y == 0 else -border/2)
		if banner_y == -1:
			banner_y = offset_y

		a = border + (count_x * border) + (count_x * resize_size[0])
	 	b = size[1] / 2 * count_y + offset_y
		c = a + resize_size[0]
		d = b + resize_size[1]
		box = (a, b, c, d)
		#print('box: {}'.format(box))
		collage.paste(resized_img, box, mask=None)
		if frame_width > 0:
			draw.rectangle(box, outline=frame_color, width=frame_width)
		
		if count_x == 1:
			count_x = 0
			count_y += 1
		else:
			count_x += 1
		resized_img.close()
		img.close()

	# check for banner
	if not (banner is None):
		b_img = Image.open(banner)
		b_w, b_h = b_img.size
		# we need banner in portrait format
		if b_w > b_h:
			b_img = b_img.rotate(90)
			b_w, b_h = b_img.size()
			#print('banner image is now {}x{}'.format(b_w, b_h))

		x = size[0] - banner_size[0] + border
		## first try bigger side
		h_factor = float(banner_size[1]) / float(b_h)
		#print('factor is {}'.format(h_factor))
		b_w_new, b_h_new = (int(b_w * h_factor), int(b_h * h_factor))
		

		if b_w_new + x > size[0]:
			w_factor =  float(banner_size[0] - border) / float(b_w)
			#print('new factor is {}'.format(w_factor))
			b_w_new, b_h_new = (int(b_w * w_factor), int(b_h * w_factor))

		b_img = b_img.resize((b_w_new, b_h_new), Image.LANCZOS)
		#print('new banner size = {}'.format((b_w_new, b_h_new)))
		
		# position in middle below the images
		y = int(float(size[1]) / 2 - float(b_h_new) / 2)
		#print('banner position: {}'.format((x,y)))

		collage.paste(b_img, (x,y))
		b_img.close()


	## grid lines for visiual feedback
	# end = size[0] - banner_size[0]
	# center of image
	# center_y = int(float(size[1]) / 2)
	# draw.line((0, center_y, size[0], center_y), 'red')
	# print('line from {},{} to {},{}'.format(0, center_y, size[0], center_y))
	# draw.line((0, border, end, border), (255, 0, 0))
	# y = size[1] / 2 - border / 2
	# draw.line((0, y, end, y), (255, 0, 0))
	# y = size[1] / 2 + border / 2
	# draw.line((0, y, end, y), (255, 0, 0))
	# draw.line((0, size[1] - border, end, size[1] - border), (255, 0, 0))

	out_file_name = 'collage.jpg'
	if not target is None:
		out_file_name = target

	collage.save(os.path.join(directory, out_file_name))
	collage.close()

if __name__ == '__main__':
	import argparse

	parser = argparse.ArgumentParser(description='Process 4 images to a collage')
	parser.add_argument('directory', help='The directory path containing the images')
	parser.add_argument('-b', '--banner', help='Optional banner image path')
	parser.add_argument('-t', '--target', help='Optional collage name')
	parser.add_argument('-w', '--frame-width', type=int, default=6, help='Optional frame width (default 6px)')
	parser.add_argument('-c', '--frame-color', help='Optional frame color as "r,g,b" string (default "0,0,0" -> black)')
	args = parser.parse_args()

	frame_color = args.frame_color
	# convert comma list of strings to needed tuple of int
	if not frame_color is None:
		frame_color = tuple(map(int, args.frame_color.split(',')))
	build_collage(args.banner, args.target, args.directory, frame_width=int(args.frame_width), frame_color=frame_color)
