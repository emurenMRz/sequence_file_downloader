#!/usr/bin/env python

import urllib.parse
import http.client
import sys
import os
import socket
import time
import re
import argparse
import textwrap

def parse_url(url):
    """
    Analyze the target URL and extract the sequential number range.

    Parameters
    ----------
    url : str
        The URL of the target files, including the sequential number range.

    Examples
    --------
    >>> print(parse_url('http://www.example.com/a[1-100].jpg'))
    {'scheme': 'http', 'host': 'www.example.com', 'port': 0, 'path': '/a[*].jpg', 'ranges': ['1-100']}
    >>> print(parse_url('http://www.example.com/b[2,4,8,10].jpg'))
    {'scheme': 'http', 'host': 'www.example.com', 'port': 0, 'path': '/b[*].jpg', 'ranges': ['2', '4', '8', '10']}
    >>> print(parse_url('http://www.example.com/c[1,2-5,7,10-13,22-25].jpg'))
    {'scheme': 'http', 'host': 'www.example.com', 'port': 0, 'path': '/c[*].jpg', 'ranges': ['1', '2-5', '7', '10-13', '22-25']}
    >>> print(parse_url('http://www.example.com/[0001-0025].jpg'))
    {'scheme': 'http', 'host': 'www.example.com', 'port': 0, 'path': '/[*].jpg', 'ranges': ['0001-0025']}
    """
    parsed_url = urllib.parse.urlparse(url)

    # Get hostname and port
    host_port = parsed_url.netloc.split(':')
    port = int(host_port[1]) if len(host_port) == 2 else 0

    # Path normalization
    path = parsed_url.path
    m = re.search(r'\[([0-9,-]+)\]', path)
    if m is None: raise ValueError("The range is not specified.")

    return {
        'scheme': parsed_url.scheme,
        'host': host_port[0],
        'port': port,
        'path': path[:m.start()] + '[*]' + path[m.end():],
        'ranges': [x.strip() for x in m.group()[1:-1].split(',') if not x.strip() == '']
        }


def get_digit(range_str):
    """
    Get the number of display digits.

    Parameters
    ----------
    range_str : str
        A string indicating a range. Corresponds to either of the
        following formats.

        * '[0-9]+'
        * '[0-9]+-[0-9]+'

    Returns
    -------
    digit
    """
    if r := re.fullmatch(r'([0-9]+)-([0-9]+)', range_str):
        return len(r.groups()[0])
    elif r := re.fullmatch(r'([0-9]+)', range_str):
        return len(r.group())
    else:
        raise ValueError("Wrong range format.")


def parse_range(range_str):
    """
    Generates an object of type range for the specified range.

    Parameters
    ----------
    range_str : str
        A string indicating a range. Corresponds to either of the
        following formats.

        * '[0-9]+'
        * '[0-9]+-[0-9]+'

    Returns
    -------
    range
    """
    if r := re.fullmatch(r'([0-9]+)-([0-9]+)', range_str):
        begin = int(r.groups()[0])
        end = int(r.groups()[1])
        if begin > end:
            begin, end = end, begin
    elif r := re.fullmatch(r'([0-9]+)', range_str):
        begin = end = int(r.group())
    else:
        raise ValueError("Wrong range format.")
    return range(begin, end + 1)


def get_content(conn, content_path, file_path):
    """
    Downloads the specified content and saves it to a file.

    Parameters
    ----------
    conn : http.client.HTTPConnection or http.client.HTTPSConnection
    content_path : str
        The path on the host of the target content.
    file_path : str
        The name of the file to be saved.
    """
    print("----------------------------------------")
    print('{0} => {1}'.format(content_path, file_path))
    try:
        conn.request('GET', content_path)

        response = conn.getresponse()
        if response.status < 300:
            content_length = int(response.getheader('Content-Length'))
            with open(file_path, mode = 'wb') as f:
                while True:
                    while chunk := response.read(4096):
                        f.write(chunk)
                        content_length -= len(chunk)
                    if content_length <= 0 or response.isclosed(): break
            if content_length != 0:
                print("    ==> Disconnected: {0} bytes remaining.".format(content_length))
                return True
        else:
            print("    ==> Result: {0} {1}".format(response.status, response.reason))
            response.read()
    except (socket.timeout, http.client.RemoteDisconnected) as e:
        print("    Exception: {0} {1}".format(type(e), e))
        return True
    except Exception as e:
        print("    Exception: {0} {1}".format(type(e), e))
    return False


def do_reconnecting(conn, interval = 60 * 3):
    """
    Wait for the specified time and reconnect.

    Parameters
    ----------
    conn : http.client.HTTPConnection or http.client.HTTPSConnection
    interval : int, default 60 * 3 (3 minutes)
        Wait time to reconnect.
    """
    for s in range(interval, -1, -1):
        unit = '' if s == 1 else 's'
        print("        ==> Reconnect after {:3d} second{}.\r".format(s, unit), end = '')
        time.sleep(1)
    conn.connect()
    print("        ==> Reconnecting.                    ")


def download(url, verbose = False):
    """
    Connect to the host and download the sequential numbered file.

    Parameters
    ----------
    url : str
        The URL of the target files, including the sequential number range.
    verbose : bool, default False
        Show detailed communication logs.
    """
    o = parse_url(url)

    if o['scheme'] == 'http': client = http.client.HTTPConnection
    if o['scheme'] == 'https': client = http.client.HTTPSConnection
    timeout = 60 * 5
    conn = client(o['host'], timeout = timeout) if o['port'] == 0 else client(o['host'], o['port'], timeout)
    if verbose: conn.set_debuglevel(1)
    conn.connect()
    print("Connection: {0}://{1}:{2}/".format(o['scheme'], conn.host, conn.port))

    try:
        reconnect = False
        for r in o['ranges']:
            digit = get_digit(r)
            for i in parse_range(r):
                if reconnect: do_reconnecting(conn)
                path = o['path'].replace('[*]', '{:>0' + str(digit) + '}').format(str(i))
                reconnect = get_content(conn, path, os.path.basename(path))
    except Exception as e:
        print(e)
    finally:
        conn.close()


def make_output_dir(output_dir = './'):
    """
    Creates a directory with the specified name and makes it the current 
    directory.

    Parameters
    ----------
    output_dir : str. default './'
        Directory path of the output destination.
    """
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        os.chdir(output_dir)
        print('Output directory: {}'.format(os.getcwd()))
    except Exception as e:
        print(e)
        exit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog = 'sndl.py',
        formatter_class = argparse.RawDescriptionHelpFormatter,
        description = textwrap.dedent('''\
            Download the sequential numbering file.  
              
            Target_URL Examples:  
            * http://www.example.com/a[1-100].jpg  
            This is the basic syntax for downloading a1.jpg ~ a100.jpg from www.example.com.  

            * http://www.example.com/b[2,4,8,10].jpg  
            If the number is skipped.  

            * http://www.example.com/c[1,2-5,7,10-13,22-25].jpg  
            The singular number and range can be mixed and matched.

            * `http://www.example.com/[0001-0025].jpg`
            Zero-padding is done according to the number of digits in the number (or the starting number in the case of a range specification).
            '''))
    parser.add_argument('-v', '--verbose', action = 'store_true', help = 'show detailed communication logs.')
    parser.add_argument('-o', '--output', type = str, help = 'specifies the path to the output directory.')
    parser.add_argument('Target_URL', type = str, help = 'the URL of the target files, including the sequential number range.')
    args = parser.parse_args()

    if len(sys.argv) <= 1:
        parser.print_help()
        exit()
    output_dir = args.output if args.output else './download'
    make_output_dir(output_dir)
    download(args.Target_URL, args.verbose)
