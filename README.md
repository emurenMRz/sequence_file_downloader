# sequence_file_downloader
Download the sequential numbering file.

## usage

> `sndl.py [-h] [-v] [-o OUTPUT] Target_URL`

## Target_URL Examples

This is the basic syntax for downloading `a1.jpg` ~ `a100.jpg` from `www.example.com`.
> `http://www.example.com/a[1-100].jpg`

If the number is skipped.
> `http://www.example.com/b[2,4,8,10].jpg`

The singular number and range can be mixed and matched.
> `http://www.example.com/c[1,2-5,7,10-13,22-25].jpg`

Zero-padding is done according to the number of digits in the number (or the starting number in the case of a range specification).
> `http://www.example.com/[0001-0025].jpg`

## License

These codes are licensed under CC0.

[![CC0](http://i.creativecommons.org/p/zero/1.0/88x31.png "CC0")](http://creativecommons.org/publicdomain/zero/1.0/deed.ja)