# encoding: utf-8
from django.conf import settings

import PIL.Image
import StringIO
import cv2
import numpy
import qrcode
import reportlab.lib.pagesizes
import reportlab.lib.units
import reportlab.lib.utils
import reportlab.pdfgen.canvas
import tempfile
import zbar

COFFEE_USE_LANDSCAPE = getattr(settings, "COFFEE_USE_LANDSCAPE", True)
COFFEE_LINE_HEIGHT = getattr(settings, "COFFEE_LINE_HEIGHT", .5)
COFFEE_BOXES_PER_LINE = getattr(settings, "COFFEE_BOXES_PER_LINE", 40)
COFFEE_NAME_FIELD_WIDTH = getattr(settings, "COFFEE_NAME_FIELD_WIDTH", 4.)
COFFEE_SHEET_PAGE_FORMAT = getattr(settings, "COFFEE_SHEET_PAGE_FORMAT",
                                   reportlab.lib.pagesizes.A4)
COFFEE_SHEET_BOTTOM_TEXT = getattr(settings, "COFFEE_SHEET_BOTTOM_TEXT", "")

if COFFEE_USE_LANDSCAPE:
    COFFEE_SHEET_PAGE_FORMAT = getattr(settings, "COFFEE_SHEET_PAGE_FORMAT",
                                       reportlab.lib.pagesizes.landscape(COFFEE_SHEET_PAGE_FORMAT))
    COFFEE_COUNT_PER_PAGE = getattr(settings, "COFFEE_COUNT_PER_PAGE", 27)
else:
    COFFEE_COUNT_PER_PAGE = getattr(settings, "COFFEE_COUNT_PER_PAGE", 43)

COFFEE_HOMEPAGE = getattr(settings, "COFFEE_HOMEPAGE", "")

def generate_lists(lists, title="Coffee list"):
    """
        Given multiple list descriptions as an iterable of list_id and names,
        generate one PDF that contains them all.

        See generate_list.
    """
    outfile = StringIO.StringIO()
    canvas = reportlab.pdfgen.canvas.Canvas(outfile, pagesize=COFFEE_SHEET_PAGE_FORMAT)
    for a_list in lists:
        generate_list(*a_list, title=title, canvas=canvas)
    canvas.save()
    return outfile

def generate_list(list_id, names, pre_cross_dict={}, title="Coffee list", canvas=None):
    """
        Generate a PDF for a coffee list

        Parameters:
            list_id: A (preferably unique) ID for this list.
                     Will be embedded as a QR code into the URL
            names:   A list of names for this list
            pre_cross_dict:
                     A dictionary mapping names to a number of crosses to pre-draw
                     onto the list
            title:   A heading for the list. Could e.g. include a date.
            canvas:  If set, draw to this canvas.

        Returns:
            A StringIO instance with the PDF file, or None if canvas is given.
    """

    assert len(names) <= COFFEE_COUNT_PER_PAGE

    # Prepare QR code
    qr_code = tempfile.NamedTemporaryFile(suffix=".png")
    qr_data = "%s?id=%d" % (COFFEE_HOMEPAGE, list_id)
    qrcode.make(qr_data, border=0).save(qr_code.name)

    # Start page, prepare units
    had_canvas = canvas is not None
    if not had_canvas:
        outfile = StringIO.StringIO()
        canvas = reportlab.pdfgen.canvas.Canvas(outfile, pagesize=COFFEE_SHEET_PAGE_FORMAT)

    width, height = COFFEE_SHEET_PAGE_FORMAT
    cm_unit = reportlab.lib.units.cm
    qr_size = 2 * cm_unit
    canvas.translate(1.5 * cm_unit, 1.5 * cm_unit)
    width -= 3 * cm_unit
    height -= 3 * cm_unit

    # Draw orientation markers
    path = canvas.beginPath()
    path.moveTo(cm_unit, height)
    path.lineTo(0, height)
    path.lineTo(0, height - cm_unit)
    canvas.setLineWidth(5)
    canvas.setLineJoin(0)
    canvas.drawPath(path)

    path = canvas.beginPath()
    path.moveTo(width, height - cm_unit)
    path.lineTo(width, height)
    path.lineTo(width - cm_unit, height)
    canvas.drawPath(path)

    path = canvas.beginPath()
    path.moveTo(width, cm_unit)
    path.lineTo(width, 0)
    path.lineTo(width - cm_unit, 0)
    canvas.drawPath(path)

    path = canvas.beginPath()
    path.moveTo(0, cm_unit)
    path.lineTo(0, 0)
    path.lineTo(cm_unit, 0)
    canvas.drawPath(path)

    canvas.setLineWidth(1)

    # Draw title
    canvas.setFont("Helvetica", 16)
    canvas.drawString(.5 * cm_unit, height - 1 * cm_unit, title)

    # Draw the QR code and ID
    canvas.drawImage(qr_code.name, .5 * cm_unit, .5 * cm_unit, qr_size, qr_size)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(.5 * cm_unit, .2 * cm_unit, "#%d" % list_id)

    # Draw bottom text
    canvas.setFont("Helvetica", 9)
    ypos = -.2
    for text in COFFEE_SHEET_BOTTOM_TEXT:
        canvas.drawString(qr_size + 1. * cm_unit, qr_size - ypos * cm_unit, text)
        ypos += .5

    # Draw grid
    grid_y = height - 2*cm_unit
    canvas.line(0, grid_y, width, grid_y)
    for name in names:
        new_y = grid_y - COFFEE_LINE_HEIGHT * cm_unit
        canvas.line(0, grid_y, 0, new_y)
        canvas.line(width, grid_y, width, new_y)
        box_start = COFFEE_NAME_FIELD_WIDTH * cm_unit
        box_width = (width - box_start) / COFFEE_BOXES_PER_LINE
        pre_draw_crosses = pre_cross_dict.get(name, 0)
        for i in range(int((width - box_start) / box_width)):
            canvas.line(box_start, grid_y, box_start, new_y)
            if pre_draw_crosses > 0:
                pre_draw_crosses -= 1
                cross_margin = 2
                canvas.line(box_start + cross_margin, grid_y - cross_margin, box_start + box_width - cross_margin, new_y + cross_margin)
                canvas.line(box_start + cross_margin, new_y + cross_margin, box_start + box_width - cross_margin, grid_y - cross_margin)
            box_start += box_width
        canvas.drawString(.2 * cm_unit, grid_y - (COFFEE_LINE_HEIGHT - .1) * cm_unit, name)
        grid_y = new_y
        canvas.line(0, grid_y, width, grid_y)

    canvas.showPage()

    if not had_canvas:
        canvas.save()
        return outfile

def detect_marks(image, expect_lines=COFFEE_COUNT_PER_PAGE):
    """
        Given a coffee list as a numpy array / OpenCV image, detect the crosses
        that were drawn onto it.

        You'd normally not use this directly. Rather, see scan_list.

        Parameters:
            image: The image
            expect_lines: The maximum number of rows to search for

        Returns:
            A tuple, (marked_image, marks, mark_y_positions), where
            marked_image is the image colored for human error checking,
            marks is an array containing a count of crosses for each line,
            and mark_y_positions is a list of the y positions where the
            line describing each user begins.
    """
    assert expect_lines <= COFFEE_COUNT_PER_PAGE

    if image.shape[1] > 5000 or image.shape[0] > 5000:
        factor = 5000. / image.shape[1]
        if image.shape[0] * factor > 1800:
            factor = 5000. / image.shape[0]
        image = cv2.resize(image, (int(image.shape[1] * factor), int(image.shape[0] * factor)))

    # 1) Find the edge markers
    imbw = cv2.threshold(cv2.cvtColor(image, cv2.COLOR_RGB2GRAY), 80, 255, cv2.THRESH_BINARY)[1]
    imbwblur = cv2.blur(imbw, (10, 10))
    imbwblurthres = cv2.threshold(imbwblur, 10, 255, cv2.THRESH_BINARY)[1]

    corners = cv2.cornerHarris(imbwblurthres, 5, 3, 0.04)
    corners = corners > 0.01 * corners.max()

    cpixels = []
    corner_coords = numpy.array(numpy.where(corners))

    for corner in ((0, 0), (imbw.shape[0], 0), (imbw.shape[0], imbw.shape[1]), (0, imbw.shape[1])):
        best_fit = numpy.sum((corner_coords - numpy.array(corner)[:,None])**2, 0).argmin()
        x, y = corner_coords[1, best_fit], corner_coords[0, best_fit]

        p = [x, y]
        while imbw[p[1], p[0]] < 128:
            p[0] += -1 if corner[1] < p[0] else 1
            p[1] += -1 if corner[0] < p[1] else 1
        cpixels.append(p)

    # 2) Perspective transform the image and select only the part inside the markers
    width, height = map(int, (numpy.array(COFFEE_SHEET_PAGE_FORMAT) / reportlab.lib.units.cm - 3.) * 100.)
    transform = cv2.getPerspectiveTransform(numpy.float32(cpixels), numpy.float32([(0, 0), (0, height), (width, height), (width, 0)]))
    im = cv2.warpPerspective(image, transform, (width, height))

    imgray = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY)
    imbw = cv2.threshold(imgray, 127, 255, cv2.THRESH_BINARY)[1]
    imbw_more = cv2.erode(cv2.adaptiveThreshold(imgray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 0), (3, 3), iterations=3)
    imbw_more = cv2.threshold(imbw_more, 10, 255, cv2.THRESH_BINARY)[1]

    # 3) Find the grid (Assuming clean borders..)
    def advance_to_field(find_line_x, find_line_y, direction, skip_border_line):
        x_sign = 1 if "e" in direction else -1 if "w" in direction else 0
        y_sign = 1 if "s" in direction else -1 if "n" in direction else 0

        if y_sign:
            while imbw[find_line_y, find_line_x] > 127:
                find_line_y += y_sign
            if skip_border_line:
                find_line_y += 5
                while imbw[find_line_y, find_line_x] < 127:
                    find_line_y += y_sign
        if x_sign:
            while imbw[find_line_y, find_line_x] > 127:
                find_line_x += x_sign
            if skip_border_line:
                find_line_x += 5
                while imbw[find_line_y, find_line_x] < 127:
                    find_line_x += x_sign
        return find_line_x, find_line_y

    find_line_x, find_line_y = advance_to_field(int(COFFEE_NAME_FIELD_WIDTH * 100) - 5, 195, "se", True)
    end_line_x, end_line_y = advance_to_field(im.shape[1] - 1, find_line_y, "w", False)

    MARK_COLOR = numpy.array([0, 255, 0])
    ERROR_COLOR = numpy.array([0, 0, 255])
    EMPTY_COLOR = numpy.array([200, 255, 255])

    markings = [ 0 ] * expect_lines
    mark_y_positions = [ 0 ] * expect_lines
    for y in range(expect_lines):
        field_width = (end_line_x - find_line_x) / COFFEE_BOXES_PER_LINE - 5
        field_height = COFFEE_LINE_HEIGHT * 100 - 5
        count = 0
        for x in range(COFFEE_BOXES_PER_LINE):
            CORNER_STRIP_X = 6
            CORNER_STRIP_Y = 10
            xp = find_line_x + x * (end_line_x - find_line_x) / COFFEE_BOXES_PER_LINE
            mark = imbw[find_line_y+CORNER_STRIP_Y:find_line_y+field_height+1-CORNER_STRIP_Y, xp+CORNER_STRIP_X:xp+field_width+1-CORNER_STRIP_X]
            mark_more = imbw_more[find_line_y+CORNER_STRIP_Y:find_line_y+field_height+1-CORNER_STRIP_Y, xp+CORNER_STRIP_X:xp+field_width+1-CORNER_STRIP_X]
            color = EMPTY_COLOR
            mean = numpy.mean(mark)
            mean2 = numpy.mean(mark_more)
            mean_halves = numpy.array([ numpy.mean(mark[:mark.shape[0]/2, :]), numpy.mean(mark[mark.shape[0]/2:, :])])
            mean2_halves = numpy.array([ numpy.mean(mark_more[:mark.shape[0]/2, :]), numpy.mean(mark_more[mark.shape[0]/2:, :])])
            if mean < 220 and mean2 < 100:
                color = ERROR_COLOR
            elif mean < 255 and mean2 < 220 and all(mean_halves + mean2_halves < 255*2):
                color = MARK_COLOR
                count += 1
            im[find_line_y:find_line_y+field_height+1, xp:xp+field_width+1] = .7 * im[find_line_y:find_line_y+field_height+1, xp:xp+field_width+1] + .3 * color
        markings[y] = count
        mark_y_positions[y] = find_line_y
        try:
            find_line_x, find_line_y = advance_to_field(int(COFFEE_NAME_FIELD_WIDTH * 100) - 5, find_line_y + 20, "se", True)
            end_line_x, end_line_y = advance_to_field(im.shape[1] - 1, find_line_y, "w", False)
        except IndexError:
            break

    return im, markings, mark_y_positions

def scan_list(image):
    """
        Given a coffee list scan as a PIL/Pillow object, detect the QR code and
        markings.

        Returns:
            A tuple, consisting of the colored image for human error checking,
            the embedded QR-code's data, the list of crosses and the y-positions
            in the image for each of the lines. See detect_marks.
    """
    bw_image = image.convert("L")
    zbar_image = zbar.Image(image.size[0], image.size[1], "Y800", bw_image.tobytes())
    processor = zbar.Processor()
    processor.init(video_device=None, enable_display=False)

    for cfg in ("enable=1 ascii=1 x-density=1 y-density=1 min-len=1").split():
        processor.parse_config(cfg)

    processor.process_image(zbar_image)

    symbols = list(zbar_image)
    assert symbols

    list_meta_data = symbols[0].data

    # Rotate the page such that the QR code is oriented correctly
    qr_code_location = numpy.array(symbols[0].location)
    first_is_left = numpy.all(qr_code_location[0, 0] - 30 < qr_code_location[:, 0])
    first_is_top = numpy.all(qr_code_location[0, 1] - 30 < qr_code_location[:, 1])
    if not first_is_top:
        image = image.rotate(180)
        first_is_left = not first_is_left
    if not first_is_left:
        image = image.rotate(90, expand=True)

    marked_image, markings, mark_y_positions = detect_marks(numpy.array(image))

    return PIL.Image.fromarray(marked_image), list_meta_data, markings, mark_y_positions
