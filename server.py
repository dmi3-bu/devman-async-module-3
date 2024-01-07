import argparse
import asyncio
import logging
import os

import aiofiles
from aiohttp import web

BYTES_IN_KB = 1024


async def archive(request):
    archive_hash_path = request.match_info['archive_hash']
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
        while not proc.stdout.at_eof():
            archive_file = await proc.stdout.read(500 * BYTES_IN_KB)
            logging.debug('Sending archive chunk ...')
            await response.write(archive_file)
            if args.latency:
                logging.debug(f'Sleeping for {args.latency} seconds ...')
                await asyncio.sleep(args.latency)
        logging.debug(f"Folder '{files_path}' zipped successfully.")
    except BaseException as e:
        logging.debug(f"{type(e)}: {e}")
        proc.kill()
        if proc.returncode is None:
            await proc.communicate()
        logging.debug("Download was interrupted")

    return response


async def handle_index_page(_request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


def prepare_args():
    parser = argparse.ArgumentParser(description='Server for zipping and downloading your files')
    parser.add_argument('-p', '--path', type=str, default='test_photos',
                        help='path to files folder')
    parser.add_argument('-l', '--logging', action='store_true',
                        help='enable logging')
    parser.add_argument('--latency', type=int,
                        help='enable latency between chunks (in seconds)')
    return parser.parse_args()


if __name__ == '__main__':
    args = prepare_args()
    if args.logging:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.disable(level=logging.DEBUG)

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
