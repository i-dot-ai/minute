# ADR-019: Fargate runtime architecture, and GitHub runner architecture

## Status

Accepted

Date of decision: 2026-03-18

## Context and Problem Statement

We need to decide whether to use arm64 or x86_64 fargate runners for our containers, and the same for our CI/CD GitHub actions runners.

## Considered Options

* arm64
* x86_64

## Decision Outcome

arm64 as it better matches our local development environment and is cheaper

## Pros and Cons of the Options

### arm64
arm64, 64-bit RISC cpu architecture. First widely used for mobile phones due to its power efficiency and open licensing but now increasingly being used for general purpose computing, most notably in Apple's M series of chips.
Because programs need to be compiled for specific CPU architectures individually, software compatibility and support on ARM lags behind x86_64. 

* Good, because it matches our local development machines as we all use M-series Macbooks. This means we're less likely to have issues where it works on our machines but not on prod for runtime / compatibility reasons
* Good, because it's approximately 20% cheaper than x86_64 ($0.03725 per vCPU per hour vs $0.04656 per vCPU per hour, and similar for the GB charges. (for eu-west-2 retrieved 20-02-2026))
* Good, because it's better for the planet, as it uses less electricity. In the cloud, cost is a very good proxy for CO2e
* Bad, because it's not what i.AI used to deploy minute in their environment. So in some way it's not 'proven' 
* Bad, because, although the compatibility with applications is improving every day, we might run into compatibility issues. That being said, see point 1.

### x86_64
x86_64, 64-bit cpu architecture. Most popular architecture and has been used across servers, laptops, and pc, for decades. Any common intel/amd cpu is x86_64

* Good, because it's the industry standard. Software and libraries should 'just work'
* Good, because it's what i.AI used to deploy minute, so we know it should work
* Bad, because it's more expensive than arm64
* Bad, because it doesn't match our local environments.
* Bad, because it's worse for the planet
