# Interface Agent: Addressing Tasks by Controlling Interfaces

<!-- [![PyPI version](https://badge.fury.io/py/interfaceagent.svg)](https://badge.fury.io/py/interfaceagent)
[![arXiv](https://img.shields.io/badge/arXiv-2303.02927-<COLOR>.svg)](https://arxiv.org/abs/2303.02927)
![PyPI - Downloads](https://img.shields.io/pypi/dm/interfaceagent?label=pypi%20downloads)

<a target="_blank" href="https://colab.research.google.com/github/microsoft/interfaceagent/blob/main/notebooks/tutorial.ipynb">
<img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a> -->

<!-- <img src="docs/images/interfaceagentscreen.png" width="100%" /> -->

Interface Agent package demonstrates how to build an agent that can accomplish tasks by driving interfaces (web browser). It combines the capabilities of large language models with web browsing to accomplish complex tasks autonomously.

## Installation

```bash
pip install interfaceagent
```

Or install the latest version from the source code:

```bash
cd interfaceagent
pip install -e .
```

## Components

1. **WebBrowser**: A wrapper around Playwright for browser control
2. **WebBrowserManager**: Manages multiple browser sessions
3. **Planner**: Uses OpenAI models to plan and execute tasks
4. **Web Api**: Provides a RESTful API to interact with the agent based on FastAPI

## Usage

```python


```
