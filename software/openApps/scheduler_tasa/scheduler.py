import sys
import time
import os

cur_path = sys.path[0]
sys.path.insert(0, os.path.join(cur_path, '..', '..', '..', '..', 'coap', 'coap'))  # coap/
sys.path.insert(0, os.path.join(cur_path, '..', '..', '..', '..', 'coapResource', 'coapResource'))  # coap/

import coap as coap
import matplotlib.pyplot as plt
import coapResource as Res
import networkx as nx

here = sys.path[0]
print (here)

topology = nx.DiGraph()
save_tab = {}
queue = {}
children = {}
coap_port = 61618  # can't be the port used in OV
f = open("try.txt", "a+")


def init_save_tab():
    global topology
    global save_tab

    save_tab = {}
    m = max(topology.nodes)
    for k in range(1, 100):
        save_tab[k] = None


def init_queue(max_=20):
    for i in range(1, 100):
        queue[i] = 1


def display_queue():
    global queue
    print queue


init_queue()


def update_metric():
    global queue
    global topology
    global children

    ret_ = nx.DiGraph()
    children = {}
    for z in list(topology.edges.data()):
        if z[2]["parent"]:
            if z[1] not in children:
                children[z[1]] = []

            if z[0] != 1:
                hum = queue[z[0]] * (20 - queue[z[1]])
            else:
                hum = queue[z[0]]
            children[z[1]].append(
                {
                    'node_id': z[0],
                    'weight': hum
                }
            )
            ret_.add_edge(z[0], z[1], weight=hum, parent=z[1], match=False)
        # print z

    return ret_


def divide_node_with_color():
    global topology
    a = nx.coloring.greedy_color(topology)
    ret = {}
    for key in a:
        col_num = a[key]
        if col_num not in ret:
            ret[col_num] = [key]
        else:
            ret[col_num].append(key)
    return ret


def get_node_color(p_node, d):
    for key in d:
        if p_node in d[key]:
            return key
    return None


def get_children(Node, graph, op=1):
    clist = []
    global children
    if op == 1:
        if Node in children:
            return children[Node]
        return []
    if Node in children:
        for element in children[Node]:
            clist.append(element["node_id"])

    return clist


# initial call with tree root
def max_weight_matching(Node, Tree):
    global save_tab
    # result was already calculated
    if save_tab[Node] is not None:
        return save_tab[Node]

    # get the set of Node's children
    chill = get_children(Node, Tree)

    # if i do not have children == Node is leaf ==> cost = 0
    if len(chill) == 0:
        save_tab[Node] = 0
        return 0

    sum1 = 0
    sum2 = 0
    chose = -1
    for elt in chill:
        if save_tab[elt["node_id"]] is None:
            max_weight_matching(elt["node_id"], Tree)
        sum1 += save_tab[elt["node_id"]]

        sum_tmp = 0
        for ch_elt in get_children(elt["node_id"], Tree):
            if save_tab[ch_elt["node_id"]] is None:
                max_weight_matching(ch_elt["node_id"], Tree)
            sum_tmp += save_tab[ch_elt["node_id"]]
        sum_tmp += Tree.edges[(elt["node_id"], Node)]["weight"]
        sum_tmp -= save_tab[elt["node_id"]]
        if sum_tmp > sum2:
            chose = elt["node_id"]
        sum2 = max(sum2, sum_tmp)
    if sum1 < sum1 + sum2:
        if Tree.edges[(chose, Node)]["weight"] != 0:
            Tree.edges[(chose, Node)]["match"] = True
        for child in get_children(chose, Tree):
            Tree.edges[(child["node_id"], chose)]["match"] = False

    save_tab[Node] = max(sum1, sum1 + sum2)
    return sum1


def get_link(node1, node2):
    global topology
    m = get_children(node1, topology, op=0)
    for elt in m:
        if elt == node2:
            return [node2, node1]

    return [node1, node2]


def get_matching(Node, Tree):
    global save_tab
    res = []
    max_weight_matching(Node, Tree)
    # print "Tree : \n\t{}\n".format(Tree.edges.data())
    for e in Tree.edges.data():
        ret_ = get_link(e[1], e[0])
        if e[2]["match"] and queue[ret_[0]] > 0 and ((20 - queue[ret_[1]]) > 0 or ret_[1] == 1):
            res.append((ret_[0], ret_[1]))
    return res, save_tab[1]


def calc_scheduler():
    init_queue(5)

    d = divide_node_with_color()
    sched = {}
    print "Coloring : \n\t{}".format(d)
    start_time = time.time()
    for i in range(40, 102):
        init_save_tab()

        ret = update_metric()

        sched[i] = {}
        res, cost = get_matching(1, ret)
        print (
            "Iter : {}\n\tCost : {} \n\tRes : \n\t\t{}\n\tQueue : {}\n\t{}\n".format(i, cost, res, queue,
                                                                                     ret.edges.data()))
        for elt in res:
            node_col = get_node_color(elt[0], d)
            if node_col not in sched[i]:
                sched[i][node_col] = []
            sched[i][node_col].append(elt[0])

            queue[elt[0]] -= 1
            if elt[1] != 1:
                queue[elt[1]] += 1
    print("--- {} seconds ---".format(time.time() - start_time))
    print "=============================================="

    print "Scheduler : \n"
    for key in sched:
        print "{} -> {}".format(key, sched[key])

    print "Queue : \n\t{}\n".format(queue)
    return sched


init_queue(20)
QUEUELENGTH = 20


def get_node_parent(num):
    global topology
    if num <= 1:
        return None
    a = list(topology.successors(num))
    for node in a:
        # print(t[num][node])
        if topology[num][node] and "parent" in topology[num][node] and topology[num][node]["parent"] == True:
            return node
    return None


def parser(payload, topo):
    global f
    print("[+] Payload parsing...!")
    global topology
    if payload[0] == 0x20:
        # announcement of one neighbor MESSAGE_TYPE 1
        print("[+] announcement of one neighbor MESSAGE_TYPE 1")
        if payload[6] == 0xFF and payload[7] == 0xFF:
            print("\t[+] GOOD FORMAT")
            from_ = payload[1] * 0xFF + payload[2]
            to_ = payload[3] * 0xFF + payload[4]
            rssi = payload[5]
            print("\t ADD {} --> {} : RSSI : {}".format(from_, to_, rssi))
            # tmp = topology.out_edges(from_)
            # topology.remove_edges_from(tmp)
            topology.add_edge(from_, to_, rssi=rssi, parent=1)
        else:
            print("\t[-] BAD FORMAT")
    elif payload[0] == 0x21:
        # [ 33   , 128,      2,            0,11,    0,7,    0,5,206, 0,7,206, 255]
        #  code   flags:p   neigh_count   from     parent  N1       N2       END
        # announcement of many neighbors MESSAGE_TYPE 1
        print("[+] announcement N neighbors")
        neighbor_count = payload[2]
        flags = payload[1]
        from_ = payload[3] * 0xFF + payload[4]
        parent = payload[5] * 0xFF + payload[6]
        print("\t ADD count = {}  -- from = {}  -- parent = {}   -- flags = {}".format(neighbor_count, from_, parent,
                                                                                       flags))
        i = 7
        for tmp in range(neighbor_count):
            to_ = payload[i] * 0xFF + payload[i + 1]
            rssi = payload[i + 2]
            print("\t\t {} --> {}  RSSI : {}".format(from_, to_, rssi))
            if to_ == parent:
                topology.add_edge(from_, to_, rssi=rssi, parent=1)
            else:
                topology.add_edge(from_, to_, rssi=rssi, parent=0)
            i = i + 3
    elif payload[0] == 120:
        now = int(round(time.time() * 1000))
        bla = payload[1:]
        string = ""
        for p in bla:
            string += chr(p)
        string = "{};{}\n".format(now, string)
        print "------> STRING : {}\n".format(string)
        f.write(string)
        print "=====INFORMATION=============\n\t{}\n".format(payload)
    else:
        # not yet implemented
        print("[!] Code is not yet implemented")
    # parsing
    print("=====================================================================\n")


def my_callback(options, payload, topo):
    print("\n[+] Payload : \n{}\n".format(payload))
    print("Code {}".format(payload[0]))
    if payload[0] == 0x20 or payload[0] == 0x21 or payload[0] == 120:
        print("[+]Payload code was recognized")
        parser(payload, topo)
    else:
        print("[-] Payload code was not recognized")


def gen_msf_disable_payload():
    return [0xff]


def gen_payload(time_freq_list):
    payload_list = {}

    payload = []
    counter = 0
    next_key = 1
    for elt in time_freq_list:
        if counter == 5:
            payload.insert(0, counter)
            payload_list[next_key] = payload
            next_key += 1
            counter = 0
            payload = []
        payload.append(elt["slot"])
        payload.append(elt["freq"])
        counter += 1
    payload.insert(0, counter)
    payload_list[next_key] = payload
    return payload_list


# my ip addr bbbb::1/64
# or sudo ip -6 addr add bbbb::1415:92cc:ffff:1 dev tun0 to add new ip addr

# MOTE_IP = 'bbbb::1415:92cc:0:2'
UDPPORT = 5683  # can't be the port used in OV
tasa_res = Res.coapResource("tasa")
tasa_res.add_put_cb(my_callback)
tasa_res.add_topo(topology)
print("[+] resources created")
# sudo ip -6 addr add bbbb::1415:92cc:ffff:1 dev tun0

c = coap.coap(udpPort=UDPPORT, ipAddress='bbbb::1')
print("[+] coap server created")

c.addResource(tasa_res)
print("[+] resources added ")


def broadcast_scheduler(table):
    global topology
    global coap_port
    global c
    nodes_count = max(topology.nodes)
    nodes = {}
    for i in range(2, nodes_count + 1):
        nodes[i] = []

    for slot in table:
        frequencies = table[slot]
        for freq in frequencies:
            devs = frequencies[freq]
            for dev in devs:  # list of nodes ids
                nodes[dev].append({"slot": slot, "freq": freq + 1})

    # req = coap.coap(udpPort=coap_port)
    mote_ip_prefix_112 = 'bbbb::1415:92cc:0:'
    print "Nodes : \n\t{}\n".format(nodes)
    for node_id in nodes:
        # payload = []
        payload = gen_msf_disable_payload()
        time_slots = nodes[node_id]
        # if len(time_slots) == 0:
        # else:
        #    payload = gen_payload(time_slots)
        node_id_hex = "{}".format(hex(node_id))[2:]
        print 'coap://[{0}]/6t'.format("{}{}".format(mote_ip_prefix_112, node_id_hex))
        print "\t{}".format(payload)
        # c.PUT('coap://[{0}]/6t'.format("{}{}".format(mote_ip_prefix_112, node_id_hex)),
        #      confirmable=False,
        #      payload=payload
        #      )
    for node_id in nodes:
        # perform_delete = True
        # payload = []
        payload_list = gen_payload(nodes[node_id])
        time_slots = nodes[node_id]
        # if len(time_slots) == 0:
        # else:
        #    payload = gen_payload(time_slots)
        node_id_hex = "{}".format(hex(node_id))[2:]
        print 'coap://[{0}]/6t'.format("{}{}".format(mote_ip_prefix_112, node_id_hex))
        print "\t{}".format(payload_list)
        for pld in payload_list:
            print "\tTOBE SENT : \n\t\t{}\n".format(payload_list[pld])
            try:
                c.PUT('coap://[{0}]/6t'.format("{}{}".format(mote_ip_prefix_112, node_id_hex)),
                      payload=payload_list[pld],
                      confirmable=False
                      )
            except:
                print "No ack was received from coap://[{0}]/6t".format("{}{}".format(mote_ip_prefix_112, node_id_hex))
            # if perform_delete:
            #    c.DELETE('coap://[{0}]/6t'.format("{}{}".format(mote_ip_prefix_112, node_id_hex)),
            #             confirmable=False,
            #             )
            #    print "DELETE SENT\n"
            #    perform_delete = False
    return nodes


def announce_scheduler():
    global c
    MOTE_IP = 'bbbb::1415:92cc:0:4'

    c.PUT('coap://[{0}]/6t'.format(MOTE_IP),
          confirmable=False,
          payload=[
              0x02, 70, 0xa, 75, 4
          ]
          )
    return 0


# read status of debug LED
# p = c.GET('coap://[{0}]/l'.format(MOTE_IP))
# print chr(p[0])
#
# toggle debug LED
# p = c.PUT(
#    'coap://[{0}]/l'.format(MOTE_IP),
#    payload = [ord('2')],
# )
#
# read status of debug LED
# p = c.GET('coap://[{0}]/l'.format(MOTE_IP))
# print chr(p[0])
#

while True:
    user_input = raw_input("cmd >> ")
    # print("Input : {}".format(input))
    if user_input == "help":
        print("""
    topo        --> display graphical plot of the current topology
    topo_text   --> display console-text view of current topology
    topo_color  --> calculate minimum number of colors for nodes
    calc_sched  --> re-launch scheduling computation
    queue       --> display queue
    anon        --> calculate scheduler and broadcast it to nodes\n
            """)
    elif user_input == "topo":
        plt.subplot(121)
        nx.draw(topology, with_labels=True, font_weight='bold')
        plt.show()
    elif user_input == "topo_txt":
        print ("Topology : ")
        print (list(topology.nodes))
        print (list(topology.edges))
    elif user_input == "queue_text":
        display_queue()
    elif user_input == "topo_color":
        print(divide_node_with_color())
    elif user_input == "calc_sched":
        s = calc_scheduler()
        broadcast_scheduler(s)
    elif user_input == "routing_txt":
        ret = update_metric()
        print "Routing : "
        print (list(ret.nodes))
        print (list(ret.edges))
    elif user_input == "routing":
        ret = update_metric()
        plt.subplot(121)
        nx.draw(ret, with_labels=True, font_weight='bold')
        plt.show()
    elif user_input == "matching":
        init_save_tab()
        init_queue(15)
        ret = update_metric()
        res, cost = get_matching(1, ret)
        print "Matching Cost ({}) \n\t{}\n".format(cost, res)
    elif user_input == "export":
        print "Data : \n{}\n".format(topology.edges.data())
    elif user_input == "anon":
        announce_scheduler()
    elif user_input == "":
        continue
    elif user_input == "close":
        f.close()
    else:
        print("Command is not valid, maybe you want try help cmd")

"""
All nodes will start announcing their connectivities , up on the receiving , they will be displayed in bottom
We can verify what we have received by typing topo_txt

we can also view it as image

now let see the RPL DO-DAG 

we can see the calculated scheduling table !!

let's check step by step how it will be distributed to nodes!


now all nodes have been received , and hopefully applied all modification to their scheduler.!!!
let's take a look at openvisualer to check scheduling table for each one !!

As we see all nodes have successfully applied the scheduling updates!!
Thank you for watching

"""
