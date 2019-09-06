# -*- coding: utf-8 -*-
def to_text(path, language='eng', psm='6'):
    """Wraps Tesseract 4 OCR with custom language model.

    Parameters
    ----------
    path : str
        path of electronic invoice in JPG or PNG format

    Returns
    -------
    extracted_str : str
        returns extracted text from image in JPG or PNG format

    """
    import subprocess
    from distutils import spawn
    import tempfile
    import time
    import logging as logger
    from PyPDF2 import PdfFileWriter, PdfFileReader

    # Check for dependencies. Needs Tesseract and Imagemagick installed.
    if not spawn.find_executable('tesseract'):
        raise EnvironmentError('tesseract not installed.')
    if not spawn.find_executable('convert'):
        raise EnvironmentError('imagemagick not installed.')
    if not spawn.find_executable('gs'):
        raise EnvironmentError('ghostscript not installed.')
    
    extracted_str = b''
    inputpdf = PdfFileReader(open(path, "rb"), strict=False)
    if inputpdf.numPages > 2:
        with tempfile.TemporaryDirectory() as tmpdirname:
            for i in range(inputpdf.numPages):
                output = PdfFileWriter()
                output.addPage(inputpdf.getPage(i))
                with open(f'{tmpdirname}/page-{i}.pdf', "wb") as outputStream:
                    output.write(outputStream)        
                with tempfile.NamedTemporaryFile(suffix='.tiff') as tf:
                    logger.debug(f'Tessract reading page-{i}')
                    # Step 1: Convert to TIFF
                    gs_cmd = [
                        'gs',
                        '-q',
                        '-dNOPAUSE',
                        '-r600x600',
                        '-sDEVICE=tiff24nc',
                        '-sOutputFile=' + tf.name,
                        f'{tmpdirname}/page-{i}.pdf',
                        '-c',
                        'quit',
                    ]
                    subprocess.Popen(gs_cmd)
                    time.sleep(3)

                    # Step 2: Enhance TIFF
                    magick_cmd = [
                        'convert',
                        tf.name,
                        '-colorspace',
                        'gray',
                        '-type',
                        'grayscale',
                        '-contrast-stretch',
                        '0',
                        '-sharpen',
                        '0x1',
                        '-density', 
                        '350', 
                        '-depth', 
                        '8',
                        'tiff:-',
                    ]

                    p1 = subprocess.Popen(magick_cmd, stdout=subprocess.PIPE)

                    # Step 3: read text from image
                    tess_cmd = ['tesseract', '-l', language, '--oem', '1', '--psm', psm, 'stdin', 'stdout']
                    p2 = subprocess.Popen(tess_cmd, stdin=p1.stdout, stdout=subprocess.PIPE)

                    out, err = p2.communicate()

                    extracted_str += out
    else:      
        with tempfile.NamedTemporaryFile(suffix='.tiff') as tf:
            logger.debug('Tessract is reading pdf.')
            # Step 1: Convert to TIFF
            gs_cmd = [
                'gs',
                '-q',
                '-dNOPAUSE',
                '-r600x600',
                '-sDEVICE=tiff24nc',
                '-sOutputFile=' + tf.name,
                path,
                '-c',
                'quit',
            ]
            subprocess.Popen(gs_cmd)
            time.sleep(3)

            # Step 2: Enhance TIFF
            magick_cmd = [
                'convert',
                tf.name,
                '-colorspace',
                'gray',
                '-type',
                'grayscale',
                '-contrast-stretch',
                '0',
                '-sharpen',
                '0x1',
                '-density', 
                '350', 
                '-depth', 
                '8',
                'tiff:-',
            ]

            p1 = subprocess.Popen(magick_cmd, stdout=subprocess.PIPE)

            # Step 3: read text from image
            tess_cmd = ['tesseract', '-l', language, '--oem', '1', '--psm', psm, 'stdin', 'stdout']
            p2 = subprocess.Popen(tess_cmd, stdin=p1.stdout, stdout=subprocess.PIPE)

            out, err = p2.communicate()

            extracted_str = out



    return extracted_str
