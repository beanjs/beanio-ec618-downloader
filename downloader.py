__VERSION__ = "1.0.0"
__AUTHOR__ = "beanjs"
__EMAIL__ = "502554248@qq.com"

import signal
from time import *
from struct import *
from argparse import ArgumentParser,ArgumentDefaultsHelpFormatter,RawTextHelpFormatter
from serial.tools import list_ports
from os.path import getsize
from binascii import hexlify,crc32
from hashlib import sha256
from serial import serialutil as serialutil,Serial

class ArgsFormatter(ArgumentDefaultsHelpFormatter, RawTextHelpFormatter):
  pass


def ERROR(message):
  print("\nERROR: {0}\n".format(message))
  flasher.port_close()
  exit(2)


def ASSERT(flag, message):
  if flag == False:
    ERROR(message)

def TOHEX(s):
    return hexlify(s).decode("ascii").upper()


class Flasher:
  def __init__(self):
    self.s = None
    pass

  def port_search(self, timeout=15):
    print("search port")
    start_time = time()
    
    while True:
      ports = list_ports.grep("17D1:0001")
      for port in ports:
        print("found port {0}".format(port.description))
        self.port = port.device
        return True
      
      if time() - start_time > timeout:
        return False
      sleep(1)

  def port_open(self):
    try:
      print(self.port)
      self.s = Serial(xonxoff=False,rtscts=False,dsrdtr=False,exclusive=None)
      self.s.port = self.port
      self.s.baudrate = 921600
      self.s.timeout = 10
      self.s.write_timeout = 10
      self.s.open()
      # help(self.s)
      # self.s.send_break()
      return True
    except serialutil.SerialException as ex:
      return False
  
  def port_close(self):
    if self.s != None:
      self.s.close()

  def port_read(self, read_size):
    r = ""
    if read_size > 0:
      r = self.s.read(read_size)
      print("<--({0}) {1}".format(len(r),TOHEX(r)))
    return r

  def port_send(self, data):
    print("-->({0}) {1}".format(len(data),TOHEX(data)))
    if len(data) > 0:
      # self.s.write(data)
      while True:
        smax = 64
        size = len(data)
        chunk = bytes()

        if size == 0:
          break
        elif smax < size:
          chunk = data[0:smax]
          data = data[smax:]
        else:
          chunk = data[0:size]
          data = data[size:]

        self.s.write(chunk)
      # print("-w>({0})".format())
      # self.s.flushOutput()

  def port_send_and_read(self,read_size,data):
    self.port_send(data)
    if read_size == 0:
      return bytes()
    # sleep(0.2)
    return self.port_read(read_size)

  def package(self, cmd, data = None):
    if data == None:
      return pack('>I',cmd)
    
    pkgLen = len(data)
    return pack('>I',cmd) + pack('<I',pkgLen) + data
    
  def package_image_head(self,fname,mask):
    #   agentboot.bin image head
    #   0x01,0x00,0x00,0x10,0x48,0x4D,0x49,0x54,0x07,0x05,0x18,0x20,0x00,0x00,0x00,0x00,
    #   0x01,0x00,0x00,0x00,0xEE,0x00,0x00,0xA4,0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x61,0x12,0xD1,0x35,0x07,0x35,0xDD,0x55,0x32,0x8C,0xAE,0xCC,0xC4,0x4C,0xFF,0x7F, # 这个SHA256 不知道从哪里来的
    #   0x2B,0xE2,0x89,0xF3,0xAD,0xD8,0xBC,0x29,0xB3,0xA2,0xC3,0x7F,0xF1,0x08,0x37,0x57, # 这个SHA256 不知道从哪里来的
    #   0x49,0x4D,0x42,0x4F,0x00,0x00,0x00,0x00,0x00,0x00,0x01,0x04,0xF0,0x8A,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x0B,0xD2,0xF3,0x94,0xB9,0xAC,0xB1,0xF4,0xAE,0x7E,0xEE,0x70,0xB8,0x77,0x4E,0x45, # agentboot.bin sha256
    #   0x7B,0xBF,0x7B,0xD2,0xA0,0xEA,0x70,0xFC,0x6E,0xA3,0x2F,0x92,0xFC,0x1E,0x98,0xE7, # agentboot.bin sha256
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00

    #   ap_bootloader.bin image head
    #   0x01,0x00,0x00,0x10,0x48,0x4D,0x49,0x54,0x07,0x05,0x18,0x20,0x00,0x00,0x00,0x00,
    #   0x01,0x00,0x00,0x00,0xEE,0x00,0x00,(0x00,0x00),0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0xB2,0x8F,0x7B,0x53,0xE0,0xC1,0x3D,0x42,0xB8,0x7F,0xE1,0x5A,0x41,0x5F,0x93,0x74,
    #   0x48,0xD9,0x43,0x0B,0xAD,0x01,0x01,0xB0,0x51,0xCE,0xE6,0xD3,0xD8,0xD0,0xCB,0x49,
    #   0x49,0x4D,0x42,0x4F,0x00,0x00,0x00,0x00,0x00,0x00,0x01,0x04,0xFE,0x90,0x01,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x76,0x27,0x54,0x51,0x99,0xAF,0x7E,0xB4,0xC6,0x8E,0xEA,0xD0,0xE8,0x6B,0xCF,0x24,
    #   0x53,0x55,0x4E,0x43,0xF0,0x17,0x61,0xA3,0xA2,0x10,0x96,0xB4,0x42,0x40,0x97,0x43,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00

    #   0x01,0x00,0x00,0x10,0x48,0x4D,0x49,0x54,0x07,0x05,0x18,0x20,0x00,0x00,0x00,0x00,
    #     01   00   00    10   48  4D   49   54   07   05   18   20   00   00   00   00
    #   0x01,0x00,0x00,0x00,0xEE,0x00,0x00,(0x00,0x04),0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #     01   00   00   00   EE   00   00    00   04    00   00   00   00   00   00   00
    #   0x84,0xF0,0xB5,0x6E,0x7E,0x8D,0xEF,0xB7,0x9F,0xE8,0xC9,0xA1,0xDB,0x61,0xF2,0x46,
    #     84   F0   B5   6E   7E   8D   EF   B7   9F   E8   C9   A1   DB   61   F2   46
    #   0x9F,0x10,0x00,0x31,0x8C,0x46,0x81,0x90,0x43,0x51,0x8C,0x34,0x5B,0x1A,0x63,0x83,
    #     9F   10   00   31   8C   46   81   90   43   51   8C   34   5B   1A   63   83
    #   (0x49,0x42,0x4B,0x44),0x00,(0x40,0x02),0x00,0x00,0x00,0x01,0x04,0x0C,0x33,0x24,0x00,
    #      49   4D   42   4F    00    00   00    00   00   00   01   04   0C   33   24   00
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #     00   00   00   00   00   00   00   00   00   00   00   00   00   00   00   00
    #   0x41,0x97,0xBC,0x82,0x1F,0xE5,0xB4,0x10,0x66,0x35,0xCF,0xC3,0x3F,0x5C,0xB0,0xD6,
    #     41   97   BC   82   1F   E5   B4   10   66   35   CF   C3   3F   5C   B0   D6
    #   0x9E,0x70,0xB1,0x98,0xBC,0x3F,0xFF,0xFD,0x8F,0x6B,0x63,0xA2,0xA3,0xB9,0x46,0xCB,
    #     9E   70   B1   98   BC   3F   FF   FD   8F   6B   63   A2   A3   B9   46   CB000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    #   0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00

    fsize = getsize(fname)
    fhandle = open(fname,'rb')
    mhead = sha256() 
    mbody = sha256()

    pkg = bytes()
    pkg = pkg + pack('>IIII',0x01000010,0x484D4954,0x07051820,0x00000000)
    pkg = pkg + pack('>IIII ',0x01000000,0xEE000000|((mask>>8)&0xFF),0x00000000|((mask&0xFF)<<24),0x00000000)
    
    # image head hash
    # mhead.update(pkg)
    # pkg = pkg + mhead.digest()
    # pkg = pkg + pack('>IIII',0x6112D135,0x0735DD55,0x328CAECC,0xC44CFF7F)
    # pkg = pkg + pack('>IIII',0x2BE289F3,0xADD8BC29,0xB3A2C37F,0xF1083757)
    # pkg = pkg + pack('>IIII',0xB28F7B53,0xE0C13D42,0xB87FE15A,0x415F9374)
    # pkg = pkg + pack('>IIII',0x48D9430B,0xAD0101B0,0x51CEE6D3,0xD8D0CB49)
    pkg = pkg + pack('>IIII',0x84F0B56E,0x7E8DEFB7,0x9FE8C9A1,0xDB61F246)
    pkg = pkg + pack('>IIII',0x9F100031,0x8C468190,0x43518C34,0x5B1A6383)

    pkg = pkg + pack('>III',0x494D424F,0x00000000,0x00000104) + pack('<I',fsize)
    pkg = pkg + pack('>IIII',0x00000000,0x00000000,0x00000000,0x00000000)
    
    # image body hash
    mbody.update(fhandle.read())
    pkg = pkg + mbody.digest()

    pkg = pkg + pack('>IIII',0x00000000,0x00000000,0x00000000,0x00000000)
    pkg = pkg + pack('>IIII',0x00000000,0x00000000,0x00000000,0x00000000)
    pkg = pkg + pack('>IIII',0x00000000,0x00000000,0x00000000,0x00000000)
    pkg = pkg + pack('>IIII',0x00000000,0x00000000,0x00000000,0x00000000)
    pkg = pkg + pack('>IIII',0x00000000,0x00000000,0x00000000,0x00000000)
    pkg = pkg + pack('>IIII',0x00000000,0x00000000,0x00000000,0x00000000)
    pkg = pkg + pack('>IIII',0x00000000,0x00000000,0x00000000,0x00000000)
    pkg = pkg + pack('>IIII',0x00000000,0x00000000,0x00000000,0x00000000)
    pkg = pkg + pack('>IIII',0x00000000,0x00000000,0x00000000,0x00000000)

    return pkg

  def package_with_checksum(self,cmd,data):
    pkgLen = len(data)
    
    pkg = pack('>I',cmd) + pack('<I',pkgLen) + data
    return pkg + pack('<I',self.checksum(pkg))

  def package_with_crc(self,cmd,mask,data):
    pkgLen = len(data)

    pkg = pack('>I',cmd) + pack('<I',pkgLen) + data
    pkg = pkg + pack('<I',crc32(pkg)&0xFFFFFFFF)

    pkg = bytearray(pkg)
    pkg[6] = (mask >> 8) & 0xFF
    pkg[7] = (mask >> 0) & 0xFF

    return pkg

  def checksum(self, data):
    checksum = 0
    for i in range(0, len(data)):
      checksum += data[i]
    return checksum & 0xFFFFFFFF

  def dl_agentboot(self):
    # W 00 D3 02 2B 
    # W 00 D3 02 2B
    # R 00 D3 02 2B
    self.port_send_and_read(0,self.package(0x00D3022B))
    ack, = unpack('>I',self.port_send_and_read(4,self.package(0x00D3022B)))
    ASSERT(ack == 0x00D3022B,'dl_agentboot echo error: 0x00D3022B')

    # W 20 00 CD 32 00 00 00 00
    # R 20 00 CD 32 00 0C
    # R 00 00 00 02 01 00 00 00 02 26 21 20 
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package(0x2000CD32,bytes())))
    self.port_read(size)
    ASSERT(ack == 0x2000CD32,'dl_agentboot echo error: 0x2000CD32')

    # W 21 00 CD 32 00 00 00 00
    # R 21 00 CD 32 00 04
    # R 48 4D 49 54
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package(0x2100CD32,bytes())))
    self.port_read(size)
    ASSERT(ack == 0x2100CD32,'dl_agentboot echo error: 0x2100CD32')

    # W 22 00 CD 32 00 00 00 00 
    # R 22 00 CD 32 00 00
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package(0x2200CD32,bytes())))
    ASSERT(ack == 0x2200CD32,'dl_agentboot echo error: 0x2200CD32')

    # W 31 00 CD 32 04 00 00 00 10 01 00 00
    #   31 00 CD 32 04 00 00 00 10 01 00 00
    # R 31 00 CD 32 00 04
    # R 10 01 00 00
    # W 32 00 CD 32 10 01 00 00 01 00 00 10 48 4D 49 54
    #   07 05 18 20 00 00 00 00 01 00 00 00 EE 00 00 A4 
    #   01 00 00 00 00 00 00 00 61 12 D1 35 07 35 DD 55 
    #   32 8C AE CC C4 4C FF 7F 2B E2 89 F3 AD D8 BC 29 
    #   B3 A2 C3 7F F1 08 37 57 49 4D 42 4F 00 00 00 00 
    #   00 00 01 04 F0 8A 00 00 00 00 00 00 00 00 00 00 
    #   00 00 00 00 00 00 00 00 0B D2 F3 94 B9 AC B1 F4 
    #   AE 7E EE 70 B8 77 4E 45 7B BF 7B D2 A0 EA 70 FC 
    #   6E A3 2F 92 FC 1E 98 E7 00 00 00 00 00 00 00 00 
    #   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 
    #   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 
    #   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 
    #   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 
    #   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 
    #   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 
    #   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 
    #   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 
    #   00 00 00 00 00 00 00 00 63 2B 00 00
    # R 32 01 CD 32 00 00
    hpkg = self.package_image_head(self.file_agentboot,0xA401)
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package(0x3100CD32,pack('<I',len(hpkg)))))
    self.port_read(size)
    ASSERT(ack == 0x3100CD32,'dl_agentboot echo error: 0x3100CD32')
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_checksum(0x3200CD32,bytes(hpkg))))
    ASSERT(ack == 0x3201CD32,'dl_agentboot echo error: 0x3201CD32')

    # W 3A 00 CD 32 00 00 00 00
    # R 3A 00 CD 32 00 00
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package(0x3A00CD32,bytes())))
    ASSERT(ack == 0x3A00CD32,'dl_agentboot echo error: 0x3A00CD32')

    # W 00 D3 02 2B 
    # W 00 D3 02 2B
    # R 00 D3 02 2B
    self.port_send_and_read(0,self.package(0x00D3022B))
    ack, = unpack('>I',self.port_send_and_read(4,self.package(0x00D3022B)))
    ASSERT(ack == 0x00D3022B,'dl_agentboot download error: 0x00D3022B')

    # W 20 00 CD 32 00 00 00 00
    # R 20 00 CD 32 00 0C
    # R 00 00 00 02 01 00 00 00 02 26 21 20
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package(0x2000CD32,bytes())))
    self.port_read(size)
    ASSERT(ack == 0x2000CD32,'dl_agentboot download error: 0x2000CD32')

    # W 21 00 CD 32 00 00 00 00
    # R 21 00 CD 32 00 04
    # R 48 4D 49 54
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package(0x2100CD32,bytes())))
    self.port_read(size)
    ASSERT(ack == 0x2100CD32,'dl_agentboot download error: 0x2100CD32')

    # W 22 00 CD 32 00 00 00 00 
    # R 22 00 CD 32 00 00
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package(0x2200CD32,bytes())))
    ASSERT(ack == 0x2200CD32,'dl_agentboot download error: 0x2200CD32')

    fsize = getsize(self.file_agentboot)
    fhandle = open(self.file_agentboot,'rb')

    step = 0
    while True:    
      chunk = fhandle.read(0x400)
      chunkSize = len(chunk)
      if chunkSize == 0:
        break
  
      ack, size = unpack('>IH',self.port_send_and_read(6,self.package(0x3100CD32,pack('<I',fsize))))
      self.port_read(size)
      ASSERT(ack == 0x3100CD32,'dl_agentboot download error: 0x3100CD32')

      ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_checksum(0x3200CD32 | ( step<<16 ),chunk)))
      step = step + 1
      fsize = fsize - chunkSize
      ASSERT(ack == 0x3200CD32 | (step << 16),'dl_agentboot download error: 0x3200CD32')
      
    fhandle.close()
    # W 3A 00 CD 32 00 00 00 00
    # R 3A 00 CD 32 00 00
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package(0x3A00CD32,bytes())))
    ASSERT(ack == 0x3A00CD32,'dl_agentboot download error: 0x3A00CD32')

  def dl_ap_bootloader(self):
    # W CD D3 02 2B 
    # W CD D3 02 2B 
    # R CD D3 02 2B
    self.port_send_and_read(0,self.package(0xCDD3022B))
    ack, = unpack('>I',self.port_send_and_read(4,self.package(0xCDD3022B)))
    ASSERT(ack == 0xCDD3022B,'dl_ap_bootloader echo error: 0xCDD3022B')

    # W 42 00 4C B3 04 00 00 9E 49 4D 42 4F 2E 82 DA 6C
    # R 42 00 4C B3 00 00
    # R 08 AD 88 E5
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x42004CB3,0x009E,pack('>I',0x494D424F))))
    self.port_read(4) # crc
    ASSERT(ack == 0x42004CB3,'dl_ap_bootloader echo error: 0xCDD3022B')

    # W AA D3 02 2B 
    # W AA D3 02 2B
    # W AA D3 02 2B
    # W AA D3 02 2B
    # R AA D3 02 2B
    self.port_send_and_read(0,self.package(0xAAD3022B))
    self.port_send_and_read(0,self.package(0xAAD3022B))
    self.port_send_and_read(0,self.package(0xAAD3022B))
    ack, = unpack('>I',self.port_send_and_read(4,self.package(0xAAD3022B)))
    ASSERT(ack == 0xAAD3022B,'dl_ap_bootloader echo error: 0xAAD3022B')
    
    # W 20 00 CD 32 00 00 00 00 B3 5B C3 EA 
    #   20 00 CD 32 00 00 00 00 B3 5B C3 EA
    # R 20 00 CD 32 00 0C 	
    # R 01 00 00 01 01 00 00 00 11 26 21 20 
    # R A0 E0 EF 9C 
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2000CD32,0x0000,bytes())))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x2000CD32,'dl_ap_bootloader echo error: 0x2000CD32')

    # W 21 00 CD 32 00 00 00 00 2D 5B 69 26
    # R 21 00 CD 32 00 04
    # R 00 00 00 00 
    # R 25 4F 95 03 
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2100CD32,0x0000,bytes())))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x2100CD32,'dl_ap_bootloader echo error: 0x2100CD32')

    # W 22 00 CD 32 00 00 00 00 CE 5C E6 A8 
    # R 22 00 CD 32 00 00
    # R BB 02 6E 58
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2200CD32,0x0000,bytes())))
    self.port_read(4) # crc
    ASSERT(ack == 0x2200CD32,'dl_ap_bootloader echo error: 0x2200CD32')

    # W 31 00 CD 32 04 00 00 9E 10 01 00 00 13 E2 4E AC 	
    # R 31 00 CD 32 00 04 	
    # R 10 01 00 00 	
    # R 85 FC BF 1E 	
    hpkg = self.package_image_head(self.file_ap_bootloader,0x0000)
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3100CD32,0x009E,pack('<I',len(hpkg)))))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x3100CD32,'dl_ap_bootloader echo error: 0x3100CD32')
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3200CD32,0x008E,bytes(hpkg))))
    ASSERT(ack == 0x3201CD32,'dl_ap_bootloader echo error: 0x3201CD32')
    self.port_read(4) # crc

    # W 3A 00 CD 32 00 00 00 00
    # R 3A 00 CD 32 00 00
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3A00CD32,0x0000,bytes())))
    self.port_read(4) # crc
    ASSERT(ack == 0x3A00CD32,'dl_ap_bootloader echo error: 0x3A00CD32')

    # W AA D3 02 2B
    # W AA D3 02 2B
    # R AA D3 02 2B
    self.port_send_and_read(0,self.package(0xAAD3022B))
    ack, = unpack('>I',self.port_send_and_read(4,self.package(0xAAD3022B)))
    ASSERT(ack == 0xAAD3022B,'dl_ap_bootloader download high error: 0xAAD3022B')

    # W 20 00 CD 32 00 00 00 00 B3 5B C3 EA 
    # R 20 00 CD 32 00 0C 	
    # R 01 00 00 01 01 00 00 00 11 26 21 20 
    # R A0 E0 EF 9C 
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2000CD32,0x0000,bytes())))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x2000CD32,'dl_ap_bootloader download high error: 0x2000CD32')

    # W 21 00 CD 32 00 00 00 00 2D 5B 69 26
    # R 21 00 CD 32 00 04
    # R 49 4D 42 4F 
    # R 67 38 B8 D2
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2100CD32,0x0000,bytes())))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x2100CD32,'dl_ap_bootloader download high error: 0x2100CD32')

    # W 22 00 CD 32 00 00 00 00 CE 5C E6 A8 
    # R 22 00 CD 32 00 00
    # R BB 02 6E 58
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2200CD32,0x0000,bytes())))
    self.port_read(4) # crc
    ASSERT(ack == 0x2200CD32,'dl_ap_bootloader download high error: 0x2200CD32')

    fsize = getsize(self.file_ap_bootloader)
    fhandle = open(self.file_ap_bootloader,'rb')

    # S FE 90 01 00
    #   00 9E 00 00 01 00 - 32 01 16384
    #   00 9E 00 C0 00 00 - 32 02 16384
    #   00 9E 00 80 00 00 - 32 03 16384
    #   00 9E 00 40 00 00 - 32 04 16384
    step = 0
    dlen = fsize&0xFFFF0000
    while True:    
      chunk = fhandle.read(0x4000)
      chunkSize = len(chunk)
      if chunkSize == 0:
        break
  
      ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3100CD32,0x009E,pack('<I',dlen))))
      self.port_read(size)
      self.port_read(4) # crc
      ASSERT(ack == 0x3100CD32,'dl_ap_bootloader download high error: 0x3100CD32')
      if chunkSize == 0x4000:
        ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3200CD32 | ( step<<16 ),0x009B,chunk)))
      else:
        ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3200CD32 | ( step<<16 ),0x0095,chunk)))
      self.port_read(4) # crc
      step = step + 1
      dlen = dlen - chunkSize
      ASSERT(ack == 0x3200CD32 | (step << 16),'dl_ap_bootloader download high error: 0x3200CD32')
      
      if dlen <= 0:
        break

    # W 3A 00 CD 32 00 00 00 00 50 76 B8 07
    # R 3A 00 CD 32 00 00
    # R 4D 82 EB B7
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3A00CD32,0x0000,bytes())))
    self.port_read(4) # crc
    ASSERT(ack == 0x3A00CD32,'dl_ap_bootloader download high error: 0x3A00CD32')

    # W AA D3 02 2B
    # W AA D3 02 2B
    # R AA D3 02 2B
    self.port_send_and_read(0,self.package(0xAAD3022B))
    ack, = unpack('>I',self.port_send_and_read(4,self.package(0xAAD3022B)))
    ASSERT(ack == 0xAAD3022B,'dl_ap_bootloader download low error: 0xAAD3022B')

    # W 20 00 CD 32 00 00 00 00 B3 5B C3 EA 
    # R 20 00 CD 32 00 0C 	
    # R 01 00 00 01 01 00 00 00 11 26 21 20 
    # R A0 E0 EF 9C 
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2000CD32,0x0000,bytes())))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x2000CD32,'dl_ap_bootloader download low error: 0x2000CD32')

    # W 21 00 CD 32 00 00 00 00 2D 5B 69 26
    # R 21 00 CD 32 00 04
    # R 49 4D 42 4F 
    # R 67 38 B8 D2
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2100CD32,0x0000,bytes())))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x2100CD32,'dl_ap_bootloader download low error: 0x2100CD32')

    # W 22 00 CD 32 00 00 00 00 CE 5C E6 A8 
    # R 22 00 CD 32 00 00
    # R BB 02 6E 58
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2200CD32,0x0000,bytes())))
    self.port_read(4) # crc
    ASSERT(ack == 0x2200CD32,'dl_ap_bootloader download low error: 0x2200CD32')

    #   00 9E FE 90 00 00 - 32 00
    #   00 9E FE 50 00 00 - 32 01
    #   00 9E FE 10 00 00 - 32 02
    step = 0
    dlen = fsize&0x0000FFFF
    while True:    
      chunk = fhandle.read(0x4000)
      chunkSize = len(chunk)
      if chunkSize == 0:
        break
  
      ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3100CD32,0x009E,pack('<I',dlen))))
      self.port_read(size)
      self.port_read(4) # crc
      ASSERT(ack == 0x3100CD32,'dl_ap_bootloader download low error: 0x3100CD32')
      if chunkSize == 0x4000:
        ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3200CD32 | ( step<<16 ),0x009B,chunk)))
      else:
        ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3200CD32 | ( step<<16 ),0x0095,chunk)))
      self.port_read(4) # crc
      step = step + 1
      dlen = dlen - chunkSize
      ASSERT(ack == 0x3200CD32 | (step << 16),'dl_ap_bootloader download low error: 0x3200CD32')
      
      if dlen <= 0:
        break

    # W 3A 00 CD 32 00 00 00 00 50 76 B8 07
    # R 3A 00 CD 32 00 00
    # R 4D 82 EB B7
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3A00CD32,0x0000,bytes())))
    self.port_read(4) # crc
    ASSERT(ack == 0x3A00CD32,'dl_ap_bootloader download low error: 0x3A00CD32')

    # W 44 00 4C B3 00 00 00 00 AD AB 08 E7
    # R 44 00 4C B3 00 04
    # R 00 00 00 00
    # R F3 EB F4 EE 
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x44004CB3,0x0000,bytes())))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x44004CB3,'dl_ap_bootloader download low error: 0x44004CB3')
    fhandle.close()

  def dl_ap_flash(self):
    # W CD D3 02 2B 
    # W CD D3 02 2B 
    # R CD D3 02 2B
    self.port_send_and_read(0,self.package(0xCDD3022B))
    ack, = unpack('>I',self.port_send_and_read(4,self.package(0xCDD3022B)))
    ASSERT(ack == 0xCDD3022B,'dl_ap_flash echo error: 0xCDD3022B')

    # W 42 00 4C B3 04 00 00 9E 49 42 4B 44 D2 A7 96
    # R 42 00 4C B3 00 00 
    # R 08 AD 88 E5 
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x42004CB3,0x009E,pack('>I',0x49424B44))))
    self.port_read(4) # crc
    ASSERT(ack == 0x42004CB3,'dl_ap_bootloader echo error: 0xCDD3022B')

    # W AA D3 02 2B 
    # W AA D3 02 2B
    # W AA D3 02 2B
    # W AA D3 02 2B
    # R AA D3 02 2B
    self.port_send_and_read(0,self.package(0xAAD3022B))
    self.port_send_and_read(0,self.package(0xAAD3022B))
    self.port_send_and_read(0,self.package(0xAAD3022B))
    ack, = unpack('>I',self.port_send_and_read(4,self.package(0xAAD3022B)))
    ASSERT(ack == 0xAAD3022B,'dl_ap_flash echo error: 0xAAD3022B')

    # W 20 00 CD 32 00 00 00 00 B3 5B C3 EA 
    # R 20 00 CD 32 00 0C 	
    # R 01 00 00 01 01 00 00 00 11 26 21 20 
    # R A0 E0 EF 9C 
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2000CD32,0x0000,bytes())))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x2000CD32,'dl_ap_flash download high error: 0x2000CD32')

    # W 21 00 CD 32 00 00 00 00 2D 5B 69 26
    # R 21 00 CD 32 00 04
    # R 48 4D 49 54  
    # R 25 4F 95 03 
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2100CD32,0x0000,bytes())))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x2100CD32,'dl_ap_flash download high error: 0x2100CD32')

    # W 22 00 CD 32 00 00 00 00 CE 5C E6 A8 
    # R 22 00 CD 32 00 00
    # R BB 02 6E 58
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2200CD32,0x0000,bytes())))
    self.port_read(4) # crc
    ASSERT(ack == 0x2200CD32,'dl_ap_bootloader echo error: 0x2200CD32')

    # W 31 00 CD 32 04 00 00 9E 10 01 00 00 13 E2 4E AC 	
    # R 31 00 CD 32 00 04 	
    # R 10 01 00 00 	
    # R 85 FC BF 1E 	
    hpkg = self.package_image_head(self.file_ap_flash,0x0004)
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3100CD32,0x009E,pack('<I',len(hpkg)))))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x3100CD32,'dl_ap_bootloader echo error: 0x3100CD32')
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3200CD32,0x008E,bytes(hpkg))))
    ASSERT(ack == 0x3201CD32,'dl_ap_bootloader echo error: 0x3201CD32')
    self.port_read(4) # crc

  def download(self):
    self.file_agentboot, self.file_ap_bootloader, self.file_ap_flash = self.firmware

    print(TOHEX(self.package_image_head(self.file_ap_flash,0x0004)))
    # print(TOHEX(self.package_with_crc(0x3200CD32,0x008E,self.package_image_head(self.file_ap_bootloader,0x0000))))
    return

    ASSERT(self.port_search(), 'unable to find device.')
    ASSERT(self.port_open(),'can`t open device.')

    self.dl_agentboot()
    self.dl_ap_bootloader()
    self.dl_ap_flash()

    self.port_close()

flasher = Flasher()

if __name__ == '__main__':

  def signal_handler(sig, frame):
    print('operation has been stopped!')
    flasher.port_close()
    exit(1)

  signal.signal(signal.SIGINT, signal_handler)

  parser = ArgumentParser(description='beanio flash tool',
                          formatter_class=ArgsFormatter)

  parser.add_argument('firmware',
                      nargs='+',
                      help="""EC618 firmware files:
  agentboot.bin ap_bootloader.bin ap_flash.bin
  """)
  parser.add_argument(
      '-v',
      '--version',
      action="version",
      version="beanio EC618 flash tool v{0}".format(__VERSION__))

  parser.parse_args(namespace=flasher)
  flasher.download()