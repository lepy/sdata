
# Timeflake
[![PyPi Latest Version](https://img.shields.io/pypi/v/timeflake)](https://pypi.org/project/timeflake/)
[![PyPi Downloads](https://img.shields.io/pypi/dw/timeflake)](https://pypi.org/project/timeflake/)
[![CircleCI Build Status](https://img.shields.io/circleci/build/github/anthonynsimon/timeflake/master)](https://circleci.com/gh/anthonynsimon/timeflake)
[![License](https://img.shields.io/github/license/anthonynsimon/timeflake)](https://github.com/anthonynsimon/timeflake/blob/master/LICENSE)

Timeflake is a 128-bit, roughly-ordered, URL-safe UUID. Inspired by Twitter's Snowflake, Instagram's ID and Firebase's PushID.


## Features

- **Fast.** Roughly ordered (K-sortable), incremental timestamp in most significant bits enables faster indexing and less fragmentation on database indices (vs UUID v1/v4).
- **Unique enough.** With 1.2e+24 unique timeflakes per millisecond, even if you're creating 50 million of them *per millisecond* the chance of a collision is still 1 in a billion. You're likely to see a collision when creating 1.3e+12 (one trillion three hundred billion) timeflakes per millisecond.*
- **Efficient.** 128 bits are used to encode a timestamp in milliseconds (48 bits) and a cryptographically generated random number (80 bits).
- **Flexible.** Out of the box encodings in 128-bit unsigned int, hex, URL-safe base62 and raw bytes. Fully compatible with uuid.UUID.

\* Please consider how the [Birthday Paradox](https://betterexplained.com/articles/understanding-the-birthday-paradox/) might affect your use case. Also read security note on this readme.

## Why?
This could be useful to you, if you're looking for a UUID with the following properties:
- You want to have UUIDs in URLs that are not predictable (vs auto-increment integers).
- They should be random, but roughly-ordered over time so that your MySQL/Postgres indices stay fast and efficient as the dataset grows.
- And simple to use across multiple machines (no coordination or centralized system required).
- It would be nice if they were compatible with standard 128-bit UUID representations (many libraries in Python handle uuid.UUID, but no third-party types).

Some existing alternatives which I considered:
- **UUIDv1** but the timestamp bytes are not sequential and gives away network information.
- **UUIDv4** but they're mostly random, and can mess up the performance on clustered indices.
- **ULID** but approach to incrementing the sequence during same millisecond makes it more predictable.
- **KSUID** but it's 160-bit, so unfortunately not compatible with standard 128-bit UUIDs.


## Usage

```python
import timeflake

# Create a random Timeflake
flake = timeflake.random()
>>> Timeflake(base62='00mx79Rjxvfgr8qat2CeQDs')

# Get the base62, int, hex or bytes representation
flake.base62
>>> '00mx79Rjxvfgr8qat2CeQDs'

flake.hex
>>> '016fa936bff0997a0a3c428548fee8c9'

flake.int
>>> 1909005012028578488143182045514754249

flake.bytes
>>> b'\x01o\xa96\xbf\xf0\x99z\n<B\x85H\xfe\xe8\xc9'

# Convert to the standard library's UUID type
flake.uuid
>>> UUID('016fa936-bff0-997a-0a3c-428548fee8c9')

# Get the timestamp component
flake.timestamp
>>> 1579091935216

# Get the random component
flake.random
>>> 724773312193627487660233

# Parse an existing flake (you can also pass bytes, hex or int representations)
timeflake.parse(from_base62='0002HCZffkHWhKPVdXxs0YH')
>>> Timeflake('0004fbc6872f70fc9e27355a499e8b6d')

# Create from a user defined timestamp or random value:
timeflake.from_values(1579091935216, 724773312193627487660233)
>>> Timeflake('016fa936bff0997a0a3c428548fee8c9')
```


## Components

The timeflake `02i2XhN7hAuaFh3MwztcMd` (base62) encodes the following:
```
# Milliseconds since unix epoch
timestamp = 1579275030563

# Cryptographically generated random number
random    = 851298578153087956398315
```

## Alphabets

A custom base62 alphabet representation is included, modified to preserve lexicographical order when sorting strings using this encoding. The `hex` representation has a max length of 32 characters, while the `base62` will be 22 characters. Padding is required to be able to derive the encoding from the string length.

The following are all valid representations of the same Timeflake:

```
int    = 1909226360721144613344160656901255403
hex    = 016fb4209023b444fd07590f81b7b0eb
base62 = 02i2XhN7hAuaFh3MwztcMd
```

## Provided extensions
### Django model fields
You can use timeflakes as primary keys for your models. These fields currently support MySQL, Postgres and Sqlite3.

Example usage:
```python
from timeflake.extensions.django import TimeflakePrimaryKeyBinary

class Item(models.Model):
    item_id = TimeflakePrimaryKeyBinary()
    # ...
```

## Note on security
Since the timestamp part is predictable, the search space within any given millisecond is 2^80 random numbers, which is meant to avoid collisions, not to secure or hide information. You should not be using timeflakes for password-reset tokens, API keys or for anything which is security sensitive. There are better libraries which are meant for this use case (for example, the standard library's [secrets module](https://docs.python.org/3/library/secrets.html)).

## Supported versions
Right now the codebase is only tested with Python 3.7+.

## Dependencies
No dependencies other than the standard library.

## Contribute
Want to hack on the project? Any kind of contribution is welcome!
Simply follow the next steps:

- Fork the project.
- Create a new branch.
- Make your changes and write tests when practical.
- Commit your changes to the new branch.
- Send a pull request, it will be reviewed shortly.
- In case you want to add a feature, please create a new issue and briefly explain what the feature would consist of. For bugs or requests, before creating an issue please check if one has already been created for it.

## Changelog
Please see the [CHANGELOG](CHANGELOG.md) for more details.

## Implementations in other languages
* [Java](https://github.com/making/timeflake4j)

## License
This project is licensed under the MIT license. Please read the [LICENSE](LICENSE) file for more details.

## Prior art

- [Sharding & IDs at Instagram](https://instagram-engineering.com/sharding-ids-at-instagram-1cf5a71e5a5c)
- [Announcing Snowflake: Twitter](https://blog.twitter.com/engineering/en_us/a/2010/announcing-snowflake.html)
- [The 2^120 Ways to Ensure Unique Identifiers](https://firebase.googleblog.com/2015/02/the-2120-ways-to-ensure-unique_68.html)
