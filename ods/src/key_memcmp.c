/*
 * Copyright (c) 2016 Open Grid Computing, Inc. All rights reserved.
 *
 * This software is available to you under a choice of one of two
 * licenses.  You may choose to be licensed under the terms of the GNU
 * General Public License (GPL) Version 2, available from the file
 * COPYING in the main directory of this source tree, or the BSD-type
 * license below:
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 *      Redistributions of source code must retain the above copyright
 *      notice, this list of conditions and the following disclaimer.
 *
 *      Redistributions in binary form must reproduce the above
 *      copyright notice, this list of conditions and the following
 *      disclaimer in the documentation and/or other materials provided
 *      with the distribution.
 *
 *      Neither the name of Open Grid Computing nor the names of any
 *      contributors may be used to endorse or promote products derived
 *      from this software without specific prior written permission.
 *
 *      Modified source versions must be plainly marked as such, and
 *      must not be misrepresented as being the original software.
 *
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

/*
 * Author: Tom Tucker tom at ogc dot us
 */
#include <string.h>
#include <ods/ods_idx.h>
#include "ods_idx_priv.h"

static const char *get_type(void)
{
	return "MEMCMP";
}

static const char *get_doc(void)
{
	return  "ODS_KEY_MEMCMP: The key is a byte array. The memcmp function is used\n"
		"                If the lengths of the two keys is not equal, but they\n"
		"                are lexically equal, up to the length of the smaller\n"
		"                key the function returns the difference in length\n"
		"                between the two keys.\n";
}

static int64_t cmp(ods_key_t a, ods_key_t b)
{
	ods_key_value_t av = ods_key_value(a);
	ods_key_value_t bv = ods_key_value(b);
	int64_t res;
	int cmp_len = av->len;
	if (cmp_len > bv->len)
		cmp_len = bv->len;
	res = memcmp((const void *)av->value, (const void *)bv->value, cmp_len);
	if (res == 0)
		return av->len - bv->len;
	return res;
}

static const char *to_str(ods_key_t key, char *str, size_t len)
{
	ods_key_value_t kv = ods_key_value(key);
	int i, cnt;
	char *s = str;
	for (i = 0; i < kv->len; i++) {
		cnt = snprintf(s, len, "%02hhX", kv->value[i]);
		s += cnt; len -= cnt;
	}
	return str;
}

static int from_str(ods_key_t key, const char *str)
{
	ods_key_value_t kv = ods_key_value(key);
	size_t cnt;
	kv->len = 0;
	do {
		uint8_t b;
		cnt = sscanf(str, "%02hhX", &b);
		if (cnt > 0) {
			kv->value[kv->len] = b;
			kv->len++;
		}
		str += 2;
	} while (cnt > 0);
	return 0;
}

static size_t size(void)
{
	return -1; /* means variable length */
}

static size_t str_size(ods_key_t key)
{
	ods_key_value_t kv = key->as.ptr;
	return kv->len + 1;
}

static struct ods_idx_comparator key_comparator = {
	get_type,
	get_doc,
	to_str,
	from_str,
	size,
	str_size,
	cmp
};

struct ods_idx_comparator *get(void)
{
	return &key_comparator;
}

