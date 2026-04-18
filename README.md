# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/Snuffy2/omada-saml-oidc/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                  |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------------------------------ | -------: | -------: | -------: | -------: | ------: | --------: |
| src/omada\_saml\_oidc/\_\_init\_\_.py                 |        3 |        0 |        0 |        0 |    100% |           |
| src/omada\_saml\_oidc/\_\_main\_\_.py                 |        7 |        7 |        2 |        0 |      0% |      3-21 |
| src/omada\_saml\_oidc/acs\_proxy.py                   |      116 |       84 |       34 |        3 |     26% |23-\>22, 25, 57-186, 192-195, 201-207, 211 |
| src/omada\_saml\_oidc/certs.py                        |       30 |        0 |        2 |        0 |    100% |           |
| src/omada\_saml\_oidc/config.py                       |      184 |       17 |       44 |       17 |     85% |47, 49, 117, 119, 121, 123, 125, 142, 144, 154, 156, 158, 189, 192-\>195, 320-\>322, 406, 418, 433, 453 |
| src/omada\_saml\_oidc/launcher.py                     |       79 |       43 |       12 |        3 |     45% |58, 62, 76-113, 119-120, 126-135, 141-147, 151 |
| src/omada\_saml\_oidc/router.py                       |      101 |       66 |       22 |        1 |     34% |83-164, 174-175, 188-193, 207-214, 218 |
| src/omada\_saml\_oidc/satosa\_config.py               |       30 |        0 |        0 |        0 |    100% |           |
| src/omada\_saml\_oidc/satosa\_plugins/\_\_init\_\_.py |        1 |        1 |        0 |        0 |      0% |         3 |
| src/omada\_saml\_oidc/satosa\_plugins/backend.py      |       12 |       12 |        2 |        0 |      0% |      3-64 |
| src/omada\_saml\_oidc/satosa\_plugins/frontend.py     |       19 |       19 |        4 |        0 |      0% |     3-101 |
| src/omada\_saml\_oidc/secrets.py                      |       13 |        0 |        2 |        0 |    100% |           |
| src/omada\_saml\_oidc/supervisor.py                   |       78 |       33 |       18 |        2 |     53% |110-154, 167-173, 191, 196 |
| **TOTAL**                                             |  **673** |  **282** |  **142** |   **26** | **55%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/Snuffy2/omada-saml-oidc/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/Snuffy2/omada-saml-oidc/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Snuffy2/omada-saml-oidc/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/Snuffy2/omada-saml-oidc/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FSnuffy2%2Fomada-saml-oidc%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/Snuffy2/omada-saml-oidc/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.