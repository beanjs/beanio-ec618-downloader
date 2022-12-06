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
      # print("<--({0}) {1}".format(len(r),TOHEX(r)))
    return r

  def port_send(self, data):
    # print("-->({0}) {1}".format(len(data),TOHEX(data)))
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
        sleep(0.001)

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
    
  def package_image_head(self,fname,magic1,magic2,magic3,magic4):
    fsize = getsize(fname)
    fhandle = open(fname,'rb')
    mhead = sha256() 
    mbody = sha256()

    pkg = bytes()
    pkg = pkg + pack('>IIII',0x01000010,0x484D4954,0x07051820,0x00000000)
    pkg = pkg + pack('>IIII ',0x01000000,magic1,magic2,0x00000000)
    
    # image head hash
    mhead.update(pkg)
    pkg = pkg + mhead.digest()
    # pkg = pkg + pack('>IIII',0x6112D135,0x0735DD55,0x328CAECC,0xC44CFF7F)
    # pkg = pkg + pack('>IIII',0x2BE289F3,0xADD8BC29,0xB3A2C37F,0xF1083757)
    # pkg = pkg + pack('>IIII',0xB28F7B53,0xE0C13D42,0xB87FE15A,0x415F9374)
    # pkg = pkg + pack('>IIII',0x48D9430B,0xAD0101B0,0x51CEE6D3,0xD8D0CB49)
    # pkg = pkg + pack('>IIII',0x84F0B56E,0x7E8DEFB7,0x9FE8C9A1,0xDB61F246)
    # pkg = pkg + pack('>IIII',0x9F100031,0x8C468190,0x43518C34,0x5B1A6383)

    if fsize % 0x4000 != 0:
      fsize = int(fsize / 0x4000)
      fsize = fsize + 1
      fsize = int(fsize * 0x4000)
      pass

    pkg = pkg + pack('>III',magic3,magic4,0x00000104) + pack('<I',fsize)
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

    hpkg = self.package_image_head(self.file_agentboot,0xEE0000A4,0x01000000,0x494D424F,0x00000000)
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
    ipkg = 0

    while True:    
      chunk = fhandle.read(0x400)
      chunkSize = len(chunk)
      if chunkSize == 0:
        break
  
      ack, size = unpack('>IH',self.port_send_and_read(6,self.package(0x3100CD32,pack('<I',fsize))))
      self.port_read(size)
      ASSERT(ack == 0x3100CD32,'dl_agentboot download error: 0x3100CD32')
      ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_checksum(0x3200CD32 | (ipkg << 16 ),chunk)))
      ipkg = ipkg + 1
      fsize = fsize - chunkSize
      ASSERT(ack == 0x3200CD32 | (ipkg << 16),'dl_agentboot download error: 0x3200CD32')
      
    fhandle.close()
    # W 3A 00 CD 32 00 00 00 00
    # R 3A 00 CD 32 00 00
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package(0x3A00CD32,bytes())))
    ASSERT(ack == 0x3A00CD32,'dl_agentboot download error: 0x3A00CD32')

  # 00 00 - 00 00
  # 04 00 - 00 9E
  # 10 01 - 00 8E
  # 00 40 - 00 9B
  # FE 10 - 00 95
  # 0C 33 - 00 C3 

  def dl_file(self,fname,magic1,magic2,magic3,magic4):
    self.port_send_and_read(0,self.package(0xAAD3022B))
    self.port_send_and_read(0,self.package(0xAAD3022B))
    self.port_send_and_read(0,self.package(0xAAD3022B))
    ack, = unpack('>I',self.port_send_and_read(4,self.package(0xAAD3022B)))
    ASSERT(ack == 0xAAD3022B,'{0} echo error: 0xAAD3022B'.format(fname))
    
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2000CD32,0x0000,bytes())))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x2000CD32,'{0} echo error: 0x2000CD32'.format(fname))

    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2100CD32,0x0000,bytes())))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x2100CD32,'{0} echo error: 0x2100CD32'.format(fname))

    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2200CD32,0x0000,bytes())))
    self.port_read(4) # crc
    ASSERT(ack == 0x2200CD32,'{0} echo error: 0x2200CD32'.format(fname))

    hpkg = self.package_image_head(fname,magic1,magic2,magic3,magic4)
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3100CD32,0x009E,pack('<I',len(hpkg)))))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x3100CD32,'{0} echo error: 0x3100CD32'.format(fname))
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3200CD32,0x008E,bytes(hpkg))))
    self.port_read(4) # crc
    ASSERT(ack == 0x3201CD32,'{0} echo error: 0x3201CD32'.format(fname))
    

    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3A00CD32,0x0000,bytes())))
    self.port_read(4) # crc
    ASSERT(ack == 0x3A00CD32,'{0} echo error: 0x3A00CD32'.format(fname))

    fsize = getsize(fname)
    fhandle = open(fname,'rb')

    mpkg = fsize & 0xFFFF0000
    while mpkg > 0:
      self.port_send_and_read(0,self.package(0xAAD3022B))
      ack, = unpack('>I',self.port_send_and_read(4,self.package(0xAAD3022B)))
      ASSERT(ack == 0xAAD3022B,'{0} download high error: 0xAAD3022B'.format(fname))

      ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2000CD32,0x0000,bytes())))
      self.port_read(size)
      self.port_read(4) # crc
      ASSERT(ack == 0x2000CD32,'{0} download high error: 0x2000CD32'.format(fname))

      ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2100CD32,0x0000,bytes())))
      self.port_read(size)
      self.port_read(4) # crc
      ASSERT(ack == 0x2100CD32,'{0} download high error: 0x2100CD32'.format(fname))

      ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2200CD32,0x0000,bytes())))
      self.port_read(4) # crc
      ASSERT(ack == 0x2200CD32,'{0} download high error: 0x2200CD32'.format(fname))

      # 9E 9B 16384
      # 9E 95 4350
      # 9E c3 13068 
      # 9E 3A 11412 2C+94-3A=  3F-3A=5
      ipkg = 0
      dlen = 0x00010000
      mpkg = mpkg - dlen
      while True:    
        chunk = fhandle.read(0x4000)
        chunkSize = len(chunk) 
        if chunkSize == 0:
          break
        
        ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3100CD32,0x009E,pack('<I',dlen))))
        self.port_read(size)
        self.port_read(4) # crc
        ASSERT(ack == 0x3100CD32,'{0} download high error: 0x3100CD32'.format(fname))
        if chunkSize == 0x4000:
          ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3200CD32 | (ipkg << 16),0x009B,chunk)))
        self.port_read(4) # crc
        ipkg = ipkg + 1
        dlen = dlen - chunkSize
        ASSERT(ack == 0x3200CD32 | (ipkg << 16),'{0} download high error: 0x3200CD32'.format(fname))
        
        if dlen <= 0:
          break

      ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3A00CD32,0x0000,bytes())))
      self.port_read(4) # crc
      ASSERT(ack == 0x3A00CD32,'{0} download high error: 0x3A00CD32'.format(fname))
      
    self.port_send_and_read(0,self.package(0xAAD3022B))
    ack, = unpack('>I',self.port_send_and_read(4,self.package(0xAAD3022B)))
    ASSERT(ack == 0xAAD3022B,'{0} download low error: 0xAAD3022B'.format(fname))

    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2000CD32,0x0000,bytes())))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x2000CD32,'{0} download low error: 0x2000CD32'.format(fname))

    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2100CD32,0x0000,bytes())))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x2100CD32,'{0} download low error: 0x2100CD32'.format(fname))

    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x2200CD32,0x0000,bytes())))
    self.port_read(4) # crc
    ASSERT(ack == 0x2200CD32,'{0} download low error: 0x2200CD32'.format(fname))

    ipkg = 0
    dlen = fsize&0x0000FFFF
    dsize = 0x4000
    
    while True:
      chunk = bytearray(dsize)
      chunkSize = fhandle.readinto(chunk)
      if chunkSize == 0:
        break

      if dlen < 0x4000:
        dlen = dsize
  
      ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3100CD32,0x009E,pack('<I',dlen))))
      self.port_read(size)
      self.port_read(4) # crc
      ASSERT(ack == 0x3100CD32,'{0} download low error: 0x3100CD32'.format(fname))
      ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3200CD32 | ( ipkg<<16 ),0x009B,chunk)))
      self.port_read(4) # crc
      ipkg = ipkg + 1
      dlen = dlen - chunkSize
      ASSERT(ack == 0x3200CD32 | (ipkg << 16),'{0} download low error: 0x3200CD32'.format(fname))
      
      if dlen <= 0:
        break

    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x3A00CD32,0x0000,bytes())))
    self.port_read(4) # crc
    ASSERT(ack == 0x3A00CD32,'{0} download low error: 0x3A00CD32'.format(fname))

    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x44004CB3,0x0000,bytes())))
    self.port_read(size)
    self.port_read(4) # crc
    ASSERT(ack == 0x44004CB3,'{0} download low error: 0x44004CB3'.format(fname))
    
    fhandle.close()  

  def download(self):
    self.file_agentboot, self.file_ap_bootloader, self.file_ap_flash, self.file_cp_flash = self.firmware

    ASSERT(self.port_search(), 'unable to find device.')
    ASSERT(self.port_open(),'can`t open device.')
    
    print('download {0}'.format(self.file_agentboot))
    self.dl_agentboot()
    
    print('download {0}'.format(self.file_ap_bootloader))
    self.port_send_and_read(0,self.package(0xCDD3022B))
    ack, = unpack('>I',self.port_send_and_read(4,self.package(0xCDD3022B)))
    ASSERT(ack == 0xCDD3022B,'{0} echo error: 0xCDD3022B'.format(self.file_ap_bootloader))
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x42004CB3,0x009E,pack('>I',0x494D424F))))
    self.port_read(4) # crc
    ASSERT(ack == 0x42004CB3,'{0} echo error: 0xCDD3022B'.format(self.file_ap_bootloader))
    self.dl_file(self.file_ap_bootloader,0xEE000000,0x00000000,0x494D424F,0x00000000)

    print('download {0}'.format(self.file_ap_flash))
    self.port_send_and_read(0,self.package(0xCDD3022B))
    ack, = unpack('>I',self.port_send_and_read(4,self.package(0xCDD3022B)))
    ASSERT(ack == 0xCDD3022B,'{0} echo error: 0xCDD3022B'.format(self.file_ap_flash))
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x42004CB3,0x009E,pack('>I',0x49424B44))))
    self.port_read(4) # crc
    ASSERT(ack == 0x42004CB3,'{0} echo error: 0xCDD3022B'.format(self.file_ap_flash))
    self.dl_file(self.file_ap_flash,0xEE000000,0x04000000,0x49424B44,0x00400200)

    print('download {0}'.format(self.file_cp_flash))
    self.port_send_and_read(0,self.package(0xCDD3022B))
    ack, = unpack('>I',self.port_send_and_read(4,self.package(0xCDD3022B)))
    ASSERT(ack == 0xCDD3022B,'{0} echo error: 0xCDD3022B'.format(self.file_cp_flash))
    ack, size = unpack('>IH',self.port_send_and_read(6,self.package_with_crc(0x42004CB3,0x00D1,pack('>IH',0x49425043,0x01E1))))
    self.port_read(4) # crc
    ASSERT(ack == 0x42004CB3,'{0} echo error: 0xCDD3022B'.format(self.file_cp_flash))
    self.dl_file(self.file_cp_flash,0xEE000000,0x00000000,0x49425043,0x00000000)

    self.port_close()
    print('all done!!')

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
  agentboot.bin ap_bootloader.bin ap_flash.bin cp_flash.bin
  """)
  parser.add_argument(
      '-v',
      '--version',
      action="version",
      version="beanio EC618 flash tool v{0}".format(__VERSION__))

  parser.parse_args(namespace=flasher)
  flasher.download()