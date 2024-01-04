import argparse
import asyncio
import logging
import os

import aiofiles
from aiohttp import web

BYTES_IN_KB = 1024

parser = argparse.ArgumentParser(description='Server for zipping and downloading your files')
parser.add_argument('-p', '--path', type=str, default='test_photos',
                    help='path to files folder')
parser.add_argument('-l', '--logging', action='store_true',
                    help='enable logging')
parser.add_argument('--latency', type=int,
                    help='enable latency between chunks (in seconds)')
args = parser.parse_args()

if args.logging:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.disable(level=logging.DEBUG)


async def archive(request):
    archive_hash_path = request.match_info.get('archive_hash')
    files_path = f'{args.path}/{archive_hash_path}'

    if not os.path.exists(files_path):
        return web.Response(text='Архив не существует или был удален', content_type='text/html')

    response = web.StreamResponse()
    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = 'attachment; filename="photos.zip"'
    await response.prepare(request)

    proc = await asyncio.create_subprocess_exec(
        'zip', '-r', '-', '.',
        cwd=files_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    try:
        while True:
            archive_file = await proc.stdout.read(500 * BYTES_IN_KB)
            logging.debug('Sending archive chunk ...')
            await response.write(archive_file)
            if args.latency:
                logging.debug(f'Sleeping for {args.latency} seconds ...')
                await asyncio.sleep(args.latency)
            if proc.stdout.at_eof():
                logging.debug(f"Folder '{files_path}' zipped successfully.")
                break
    except BaseException as e:
        logging.debug(type(e))
        logging.debug(e)
        proc.terminate()
        logging.debug("Download was interrupted")
    finally:
        await proc.communicate()
        return response


async def handle_index_page(_request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
