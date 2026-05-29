"""Read ds_stk.dat with correct format and return ST/suspended status map."""
import struct

DS_STK_FILE = r'C:\zd_zxzq_gm\T0002\hq_cache\ds_stk.dat'
A_PREFIXES = {'600','601','603','605','688','000','001','002','003','300','301','430','830',
              '831','832','833','834','835','836','837','838','839','870','871','872','873','920'}

RECORD_SIZE = 288
CODE_OFFSET = 2
NAME_OFFSET = 20  # GBK encoded, 8 bytes
STATUS_OFFSET = 126  # 4-byte int: 0=normal, 1=ST, 2=*ST, 3=退市

def parse_ds_stk_status(filepath=None):
    """Parse ds_stk.dat and return {code: {'is_st': bool, 'is_suspended': bool}}."""
    if filepath is None:
        filepath = DS_STK_FILE
    
    result = {}
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # Skip first few records (header)
        for rec_idx in range(3, len(data) // RECORD_SIZE):
            offset = rec_idx * RECORD_SIZE
            if offset + RECORD_SIZE > len(data):
                break
            
            rec = data[offset:offset+RECORD_SIZE]
            code = rec[CODE_OFFSET:CODE_OFFSET+6].decode('ascii', errors='ignore').strip('\x00')
            
            if code[:3] not in A_PREFIXES or not code.isdigit():
                continue
            
            # Status flag
            status = int.from_bytes(rec[STATUS_OFFSET:STATUS_OFFSET+4], 'little')
            
            # Name (for reference)
            name = rec[NAME_OFFSET:NAME_OFFSET+8].decode('gbk', errors='ignore').strip('\x00').strip()
            
            result[code] = {
                'is_st': status in (1, 2),
                'is_suspended': False,  # 停牌由其他机制判断
                'st_status': status,
                'name': name,
            }
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"ds_stk.dat解析失败: {e}")
    
    return result

# Quick test
if __name__ == '__main__':
    st = parse_ds_stk_status()
    print(f"Total stocks: {len(st)}")
    st_count = sum(1 for s in st.values() if s['is_st'])
    print(f"ST stocks: {st_count}")
    for code, info in sorted(st.items())[:5]:
        print(f"  {code}: {info}")
    # Show ST stocks
    print("\nST stock examples:")
    shown = 0
    for code, info in sorted(st.items()):
        if info['is_st']:
            print(f"  {code}: {info['name']} (status={info['st_status']})")
            shown += 1
            if shown >= 10:
                break
    if shown == 0:
        print("  (none found - checking status values...)")
        from collections import Counter
        c = Counter()
        for info in st.values():
            c[info['st_status']] += 1
        print(f"  Status distribution: {dict(c)}")
