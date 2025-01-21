# Multi-Agent Systems with AutoGen

This repository contains code examples for building multi-agent applications (powered by generative AI models) based on the [AutoGen](https://github.com/microsoft/autogen) framework and is the official code repository for the book - [Multi-Agent Systems with AutoGen](https://mng.bz/eVP9), published by Manning Publications.

[![Multi-Agent Systems with AutoGen Manning Early Access Program](/docs/images/bookcover.png)](https://mng.bz/eVP9)

The book is currently available for pre-order in the [Manning Early Access Program](https://mng.bz/eVP9) (only the first few chapters are available currently).

Pre-order the book now at https://mng.bz/eVP9.

> [!TIP]
> 🔥🔥 Use the code **mldibia** for a 50% discount, valid until **August 5th**.

In [Multi-Agent Systems with AutoGen](https://mng.bz/eVP9), you will learn about the core components of agents (Generative AI models, tools, memory, orchestration), how to implement them in python code using the AutoGen framework, how to evaluate, optimize and deploy them in your applications. Overall, the book will cover:

- Core components for multi-agent systems and their implementation
- UX design principles for multi-agent systems
- Building agents to interact with various interface (web, mobile, desktop)
- Evaluating your multi-agent system using benchmarks like GAIA, GPTQ, SWEBench and your own custom benchmarks
- Performance optimization (e.g., agent-specific model tuning and parallel processing)
- Use case deep dives like data analysis, customer service, and creativity workflows.

### Useful Links

- Link to official [source code on GiHub](https://github.com/victordibia/multiagent-systems-with-autogen)
- Link to book on [Manning.com](https://mng.bz/eVP9)
- Link to book website (interactive demos, about authors etc) - https://multiagentbook.com/

> [!NOTE]
> If you downloaded the code bundle from the Manning website, please consider visiting the official code repository on GitHub at https://github.com/victordibia/multiagent-systems-with-autogen for the latest updates.

To download a copy of this code repository, click on the [Download Zip](https://github.com/victordibia/multiagent-systems-with-autogen/archive/refs/heads/main.zip) button or run the following code from your terminal.

```bash
git clone --depth 1 https https://github.com/victordibia/multiagent-systems-with-autogen.git
```

## Getting Jupyter Notebooks to work on your computer

This section explains how to install the pre-requisite libraries so that you can use the notebooks within this book. So that the libraries are safely installed for the context of this book, we use the python [virtual environment](https://docs.python.org/3/library/venv.html) concept.

1. [Install](https://www.python.org/downloads/) Python on your computer. Recommended versions are 3.9 through 3.12
2. Clone the repository: `git clone https://github.com/victordibia/multiagent-systems-with-autogen.git`
3. Go into the directory: `cd multiagent-systems-with-autogen`
4. Create a virtual environment: `python -m venv venv`
5. Activate the virtual environment: `. ./venv/bin/activate`
6. Install the required libraries into this environment: `pip install -r requirements.txt`
7. Run Jupyter Lab: `jupyter lab`
8. Within Jupyter Lab, change directories into the respective chapter and open the python notebooks.

## Table of Contents

The code in this repo is organized into chapters (shown in the table). Each chapter contains code for the various concepts and tools discussed in the book.

<!-- chapter, description, code links
1. Understanding Multi-Agent Systems.  no code
2. Building Your First Multi-Agent Application /ch02
3. THE USER EXPERIENCE (UX) OF MULTI-AGENT SYSTEMS
  -->

| Chapter | Description                                      | Code                                                                                                                                            |
| ------- | ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 1       | Understanding Multi-Agent Systems                | no code                                                                                                                                         |
| 2       | Building Your First Multi-Agent Application      | - [Your first multi-agent application](/ch02/ch2_first_application.ipynb) <br> - [Orchestrating groups of agents](/ch02/ch2_agent_groups.ipynb) |
| 3       | The User Experience (UX) for Multi-Agent Systems | no code                                                                                                                                         |
| 4       | Interface Agents                                 | - [Interface library (built from scratch)](/src/interface) <br> - [Implementing an interface agent notebook](/ch04/interface_agents.ipynb)      |

## Questions and Feedback

If you have any questions or feedback about the book or the code in this repository, please feel free to open an [issue]().

For questions about the AutoGen framework, you can also visit the [AutoGen GitHub repository](https://github.com/microsoft/autogen) or the [AutoGen documentation](https://microsoft.github.io/autogen/).

### Citation

If you find this book or code useful for your research, please consider citing it:

```
@book{multiagentsystems2024,
  author       = {Dibia, Victor},
  title        = {Multi-Agent Systems with AutoGen},
  publisher    = {Manning},
  year         = {2024},
  isbn         = {9781633436145},
  url          = {https://www.manning.com/books/multi-agent-systems-with-autogen},
  github       = {https://github.com/victordibia/multiagent-systems-with-autogen}
}
```
