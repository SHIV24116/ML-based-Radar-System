#pragma once

#include "Config.h"

constexpr int TENSOR_ARENA_SIZE = 16 * 1024;
alignas(16) static unsigned char tensorArena[TENSOR_ARENA_SIZE];
